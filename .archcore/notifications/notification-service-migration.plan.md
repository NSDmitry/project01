---
title: "План выноса доставки уведомлений в notification-service"
status: accepted
tags:
  - "domain:notifications"
  - "notifications"
---

## Goal

Вынести доставку уведомлений в отдельный сервис notification-service по принятому ADR, не меняя outbox-контракт доменов монолита: threads и bookclubs продолжают писать через `NotificationRepository`, монолит остаётся владельцем событий, сервис - владельцем доставки.

## Tasks

Фаза 1 - сервис (автономно, без интеграции с монолитом):

1. Каркас notification-service в репозитории монолита: top-level каталог `notification_service/` с собственными pyproject, Dockerfile, настройками и миграциями; FastAPI-приложение, собственная PostgreSQL, миграция таблицы `deliveries` с UNIQUE `event_id` и частичным индексом pending. Каталог самодостаточен: импорты между `app/` и `notification_service/` запрещены в обе стороны, единственный контракт - HTTP из спека границы; переезд в отдельный репозиторий (при втором потребителе или отдельной команде - условия из ADR) сводится к `git mv` + перенос CI.
2. `POST /v1/notifications:batch`: идемпотентная вставка (ON CONFLICT DO NOTHING), проверка `X-Internal-Token`, ответы 202/401/422; `GET /health`.
3. Воркер доставки: перенос канала Telegram из @app/notifications/sender.py и цикла доставки из @app/notifications/tasks.py; выборка FOR UPDATE SKIP LOCKED, лимит 5 попыток.
4. Тесты сервиса: идемпотентность повторного батча, 401 без токена, атомарность 422, доставка/ретраи/лимит попыток (перенос tests/notifications/test_notification_delivery.py).

Фаза 2 - relay в монолите:

5. Переписать @app/notifications/tasks.py в relay: выборка outbox, резолв получателя (`disabled_notifications`, `telegram_id`), POST батчем, закрытие строк по 202.
6. Удалить из монолита sender.py и `TELEGRAM_BOT_TOKEN`; дедлайн-напоминания не трогать - они пишут в outbox и уезжают через relay как любое событие.
7. Обновить спек outbox-очереди в том же изменении: нормативы доставки уезжают в спек сервиса, появляется relay.
8. Тесты relay с моком сервиса: 202 закрывает строки, недоступность сервиса оставляет их в outbox, фильтры disabled/без-канала закрывают без отправки.

Фаза 3 - деплой:

9. docker-compose: база `notifications-db`, сервис собственным образом (из `notification_service/Dockerfile`) с двумя command (api и worker-цикл); контейнер `notifier` переключается на relay.
10. Секреты: `X-Internal-Token` в окружениях монолита и сервиса, `TELEGRAM_BOT_TOKEN` только в окружении сервиса.
11. E2E-прогон: событие в монолите доходит до Telegram-мока через сервис; пауза сервиса не теряет уведомлений.

## Acceptance Criteria

- Существующие outbox-тесты монолита (tests/notifications/test_notification_outbox.py, test_deadline_reminders.py) проходят без правок - контракт создания событий не тронут.
- Тесты фаз 1-2 зелёные; mypy без ошибок в обоих проектах.
- В `notification_service/` нет импортов из `app/` и наоборот (проверка grep-ом по import в ревью фазы 1).
- E2E: остановка сервиса на 5+ минут с последующим стартом доставляет все накопленные уведомления; в `deliveries` нет дублей `event_id`.
- В окружении монолита отсутствует `TELEGRAM_BOT_TOKEN`.

## Dependencies

- PR #88 (задача #57: outbox, воркер, настройки) смержен в main - точка старта фазы 2.
- Секрет `X-Internal-Token` заведён в окружениях деплоя.
- Подтверждена хотя бы одна цель выноса из ADR (независимый деплой каналов, изоляция токенов, второй потребитель) - иначе остаёмся на фазе 0: контейнер `notifier` внутри монолита.