---
title: "Notification-service: приём батчей, очередь доставки, каналы и relay монолита"
status: accepted
tags:
  - "domain:notifications"
  - "notifications"
  - "spec"
---

## Purpose & Scope

Контракт границы "монолит - notification-service" при выносе доставки уведомлений: HTTP-приём батчей, очередь `deliveries`, воркер и каналы сервиса, обязанности relay монолита. Зависят: relay монолита (клиент API) и провайдеры каналов (Telegram). Создание событий, фан-аут, рендер текста и настройки получателей остаются за монолитом и нормируются спеком outbox-очереди. Сервис реализован самодостаточным каталогом `notification_service/` в репозитории монолита (свои pyproject, Dockerfile, настройки, миграции; импорты между `app/` и `notification_service/` запрещены в обе стороны), relay - @app/notifications/tasks.py.

## Surface

- `POST /v1/notifications:batch` - тело: массив до 500 элементов `{event_id: int, telegram_chat_id: int, text: str}`; `event_id` - id строки outbox монолита (`notifications.id`); ответы 202 / 401 / 422; аутентификация - заголовок `X-Internal-Token` со статическим секретом.
- `GET /health` - liveness для docker-compose.
- Таблица сервиса `deliveries`: `id`, `event_id` (UNIQUE), `chat_id`, `text`, `attempts`, `processed_at`, `created_at`; частичный индекс по `processed_at IS NULL`.
- Relay - цикл в монолите @app/notifications/tasks.py; источник строк - outbox `notifications` (@app/notifications/repository.py).
- Каналы сервиса - функции вида `send_telegram` в @notification_service/service/channels.py, реестр каналов - список `CHANNELS` в коде воркера @notification_service/service/worker.py.

## Normative Behavior

1. Relay MUST выбирать из outbox строки `processed_at IS NULL` через FOR UPDATE SKIP LOCKED.
2. WHEN тип уведомления входит в `users.disabled_notifications` получателя, relay MUST закрыть строку outbox без отправки в сервис.
3. WHEN у получателя нет ни одной привязки канала (нет `telegram_id`), relay MUST закрыть строку outbox без отправки.
4. Relay MUST отправлять отобранные строки одним запросом `POST /v1/notifications:batch` (до 500 элементов: `event_id` = id строки outbox, снапшот `telegram_chat_id`, готовый `text`).
5. Relay MUST помечать строки outbox обработанными только после ответа 202.
6. WHEN сервис получает валидный батч, он MUST сохранить элементы в `deliveries` вставкой с ON CONFLICT (`event_id`) DO NOTHING.
7. WHEN сервис сохранил батч, он MUST ответить 202 без выполнения синхронной доставки.
8. Воркер сервиса MUST выбирать строки `processed_at IS NULL AND attempts < 5` через FOR UPDATE SKIP LOCKED.
9. WHEN хотя бы один канал вернул True, воркер MUST закрыть строку (`processed_at`).
10. WHEN все применимые каналы вернули False, воркер MUST инкрементировать `attempts`, оставив строку в очереди.
11. WHEN все каналы вернули None (ни один не применим), воркер MUST закрыть строку без отправки.
12. Новый канал доставки MUST подключаться функцией `(chat-реквизиты, text) -> bool | None` и строкой в реестре каналов - без изменения приёма, схемы и relay.

## Constraints & Invariants

- Инвариант: путь outbox -> relay -> приём даёт at-least-once; потерянный ответ 202 ведёт к повторному POST, дубль гасится UNIQUE `deliveries.event_id`.
- Инвариант: `processed_at` NOT NULL означает "обработано окончательно"; повторная обработка такой строки невозможна.
- Инвариант: строка `deliveries` с `attempts >= 5` выпадает из выборки воркера навсегда.
- Ограничение: сервис MUST NOT обращаться к БД монолита; единственные данные получателя в сервисе - снапшот `telegram_chat_id`, переданный relay (окно устаревания равно интервалу relay, 60 с).
- Ограничение: токен отправки `TELEGRAM_BOT_TOKEN` нужен только воркеру сервиса; в окружении монолита тот же токен остаётся исключительно для проверки подписи Telegram initData при логине (IAM) - канального кода в монолите нет. `X-Internal-Token` (переменная `INTERNAL_TOKEN`) - в окружениях монолита и сервиса; пустой токен на стороне сервиса закрывает приём (любой запрос - 401).
- Ограничение: латентность доставки ограничена суммой интервалов relay и воркера сервиса; [expected] до ~2 минут при интервале 60 с у обоих.

## Failure Behavior

1. IF сервис недоступен или ответил не-202, THEN relay MUST оставить строки outbox необработанными до следующего прогона - outbox копит без потерь и без лимита попыток.
2. IF заголовок `X-Internal-Token` отсутствует или неверен, THEN сервис MUST ответить 401, не меняя состояние БД.
3. IF тело батча не проходит валидацию, THEN сервис MUST ответить 422, не сохранив ни одной строки батча.
4. IF провайдер канала недоступен или ответил ошибкой, THEN канал MUST вернуть False с записью причины в лог - воркер повторит до лимита попыток.

## Conformance

Реализация конформна, когда выполняет поведения 1-12, держит инварианты и правила отказов 1-4. Проверяется тестами relay в монолите (tests/notifications/test_notification_relay.py, мок сервиса) и тестами приёма/доставки в сервисе (notification_service/tests/).

```
Given: строка outbox с event_id E отправлена, ответ 202 потерян сетью
When: relay повторяет POST с event_id E на следующем прогоне
Then: в deliveries ровно одна строка с event_id E
```