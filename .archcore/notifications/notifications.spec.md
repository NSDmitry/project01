---
title: "Notifications: outbox-очередь и relay в notification-service"
status: accepted
tags:
  - "domain:notifications"
  - "notifications"
  - "spec"
---

## Purpose & Scope
Контракт домена уведомлений в монолите: outbox-таблица `notifications`, relay @app/notifications/tasks.py, репозиторий @app/notifications/repository.py. Потребители - домены threads и bookclubs (кладут события через `NotificationRepository` из @app/notifications/deps.py) и cron-запуск relay. Доставка по каналам выполняется отдельным сервисом notification-service и нормируется его спеком (см. @.archcore/notifications/notification-service.spec.md); канального кода в монолите нет. HTTP-роутера у домена нет: настройки пользователя живут в IAM (см. @.archcore/iam/iam-router.spec.md). Вне scope: какие именно события кладут соседние домены (их спеки).

## Surface
- `NotificationRepository`: `add` (одно уведомление), `add_for_club_members` (всем участникам клуба, кроме инициатора, одним INSERT..SELECT), `pick_pending` (пачка до 500 недоставленных), `create_deadline_reminders` (напоминания о завтрашних дедлайнах).
- Relay: `python -m app.notifications.tasks` - запускается по расписанию вне процесса приложения (docker-compose сервис `notifier`, раз в минуту); функция `relay_pending` обрабатывает одну пачку за прогон и передаёт её в notification-service (`POST /v1/notifications:batch`, заголовок `X-Internal-Token`).
- Настройки relay: `NOTIFICATION_SERVICE_URL` (адрес сервиса) и `INTERNAL_TOKEN` (общий секрет приёма батчей).
- Типы уведомлений (`NotificationType`, @app/notifications/models.py): `comment_in_thread`, `reading_started`, `stage_deadline`, `reading_deadline`.

## Normative Behavior
1. Уведомление MUST создаваться в той же транзакции, что и породившее его событие (outbox): упавшая транзакция не оставляет уведомления, успешная не теряет его. Брокер сообщений MUST NOT использоваться.
2. Текст уведомления MUST рендериться в момент события и храниться готовым в строке - relay и сервис не собирают контекст (названия клуба, треда) заново.
3. WHEN relay запускается, он MUST сначала сгенерировать напоминания о дедлайнах, затем передать пачку недоставленных строк (`processed_at IS NULL`).
4. `create_deadline_reminders` MUST создавать напоминания всем участникам клуба о дедлайне этапа (`stage_deadline`) и захода (`reading_deadline`), наступающем завтра, только для незакрытых заходов. Прогон MUST быть идемпотентным: `dedup_key` уникален, повтор гасится ON CONFLICT DO NOTHING. Дата входит в `dedup_key` - перенос дедлайна порождает новое напоминание.
5. `pick_pending` MUST выбирать строки FOR UPDATE SKIP LOCKED: два одновременных прогона relay MUST NOT передать одну строку дважды.
6. WHEN тип уведомления входит в `users.disabled_notifications` получателя, relay MUST закрыть строку без передачи в сервис. Фильтр отключённых типов применяется в момент relay, а не создания.
7. WHEN у получателя нет ни одной привязки канала (нет `telegram_id`), relay MUST закрыть строку без передачи: пользователь без Telegram не копит вечную очередь.
8. Relay MUST передавать отобранные строки одним запросом `POST /v1/notifications:batch` (`event_id` = id строки outbox, снапшот `telegram_chat_id`, готовый `text`) и MUST помечать строки обработанными только после ответа 202.

## Constraints & Invariants
- Инвариант: `processed_at` не NULL означает "обработано" - передано сервису, отключено получателем либо доставлять некуда; повторная передача такой строки невозможна.
- Инвариант: `notifications.user_id` - FK на users с ON DELETE CASCADE: очередь пользователя живёт ровно столько, сколько он сам.
- Ограничение: relay обрабатывает одну пачку (до 500 строк) за прогон - хвост дольёт следующий запуск по расписанию. Латентность доставки складывается из интервала relay и интервала воркера сервиса (по минуте в docker-compose).
- Ограничение: частичный индекс `ix_notifications_pending` (id WHERE processed_at IS NULL) обслуживает скан relay; обработанные строки в него не попадают.
- Колонка `attempts` в outbox relay-ем не инкрементируется: ретраи и лимит попыток доставки живут в `deliveries` сервиса.

## Failure Behavior
1. IF notification-service недоступен или ответил не-202, THEN relay MUST оставить строки outbox необработанными до следующего прогона - outbox копит без потерь и без лимита попыток; дубль повторной передачи гасится идемпотентным приёмом сервиса (UNIQUE `event_id`).
2. IF получатель удалён между созданием уведомления и relay (гонка с каскадом), THEN relay MUST закрыть строку без передачи.

## Conformance
Реализация конформна, когда выполняет поведения 1-8, держит инварианты и правила отказов 1-2. Проверяется тестами tests/notifications/ (relay - с моком сервиса).