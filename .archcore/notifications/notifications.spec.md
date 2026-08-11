---
title: "Notifications: outbox-очередь, воркер доставки, каналы"
status: accepted
tags:
  - "domain:notifications"
  - "notifications"
  - "spec"
---

## Purpose & Scope
Контракт домена уведомлений: outbox-таблица `notifications`, воркер доставки @app/notifications/tasks.py, каналы @app/notifications/sender.py, репозиторий @app/notifications/repository.py. Потребители - домены threads и bookclubs (кладут события через `NotificationRepository` из @app/notifications/deps.py) и cron-запуск воркера. HTTP-роутера у домена нет: настройки пользователя живут в IAM (см. @.archcore/iam/iam-router.spec.md). Вне scope: какие именно события кладут соседние домены (их спеки).

## Surface
- `NotificationRepository`: `add` (одно уведомление), `add_for_club_members` (всем участникам клуба, кроме инициатора, одним INSERT..SELECT), `pick_pending` (пачка до 500 недоставленных), `create_deadline_reminders` (напоминания о завтрашних дедлайнах), константа `MAX_ATTEMPTS = 5`.
- Воркер: `python -m app.notifications.tasks` - запускается по расписанию вне процесса приложения (docker-compose сервис `notifier`, раз в минуту); функция `deliver_pending` обрабатывает одну пачку за прогон.
- Каналы: функции `(user, text) -> bool | None` в @app/notifications/sender.py, список активных - `CHANNELS` в @app/notifications/tasks.py. Сейчас единственный канал - `send_telegram` (Bot API sendMessage по `users.telegram_id`, токен `TELEGRAM_BOT_TOKEN`).
- Типы уведомлений (`NotificationType`, @app/notifications/models.py): `comment_in_thread`, `reading_started`, `stage_deadline`, `reading_deadline`.

## Normative Behavior
1. Уведомление MUST создаваться в той же транзакции, что и породившее его событие (outbox): упавшая транзакция не оставляет уведомления, успешная не теряет его. Брокер сообщений MUST NOT использоваться.
2. Текст уведомления MUST рендериться в момент события и храниться готовым в строке - воркер не собирает контекст (названия клуба, треда) заново.
3. WHEN воркер запускается, он MUST сначала сгенерировать напоминания о дедлайнах, затем доставить пачку недоставленных строк (`processed_at IS NULL AND attempts < MAX_ATTEMPTS`).
4. `create_deadline_reminders` MUST создавать напоминания всем участникам клуба о дедлайне этапа (`stage_deadline`) и захода (`reading_deadline`), наступающем завтра, только для незакрытых заходов. Прогон MUST быть идемпотентным: `dedup_key` уникален, повтор гасится ON CONFLICT DO NOTHING. Дата входит в `dedup_key` - перенос дедлайна порождает новое напоминание.
5. `pick_pending` MUST выбирать строки FOR UPDATE SKIP LOCKED: два одновременных прогона воркера MUST NOT отправить одну строку дважды.
6. WHEN тип уведомления входит в `users.disabled_notifications` получателя, воркер MUST закрыть строку без отправки. Фильтр отключённых типов применяется в момент доставки, а не создания.
7. WHEN ни один канал к получателю неприменим (канал вернул None - например, нет `telegram_id`), воркер MUST закрыть строку без отправки: пользователь без Telegram не ломает доставку и не копит вечную очередь.
8. WHEN хотя бы один канал доставил (True), строка MUST закрываться (`processed_at`); WHEN все применимые каналы вернули False, воркер MUST инкрементировать `attempts` и оставить строку в очереди.
9. Новый канал доставки (email, sms, push) MUST подключаться добавлением функции той же сигнатуры в sender.py и строки в `CHANNELS` - без изменения воркера, репозитория и схемы.

## Constraints & Invariants
- Инвариант: `processed_at` не NULL означает "обработано" - доставлено, отключено получателем либо доставлять некуда; повторная отправка такой строки невозможна.
- Инвариант: строка с `attempts >= MAX_ATTEMPTS` выпадает из выборки воркера навсегда (например, пользователь заблокировал бота - Telegram отвечает 403 на каждую попытку).
- Инвариант: `notifications.user_id` - FK на users с ON DELETE CASCADE: очередь пользователя живёт ровно столько, сколько он сам.
- Ограничение: воркер обрабатывает одну пачку (до 500 строк) за прогон - хвост дольёт следующий запуск по расписанию. Латентность доставки ограничена интервалом запуска (минута в docker-compose).
- Ограничение: частичный индекс `ix_notifications_pending` (id WHERE processed_at IS NULL) обслуживает скан воркера; обработанные строки в него не попадают.

## Failure Behavior
1. IF Telegram недоступен или ответил не-200, THEN канал MUST вернуть False и залогировать причину - воркер повторит на следующем прогоне до `MAX_ATTEMPTS`.
2. IF `TELEGRAM_BOT_TOKEN` не задан, THEN канал MUST вернуть False с warning в лог, не роняя воркер.
3. IF получатель удалён между созданием уведомления и доставкой (гонка с каскадом), THEN воркер MUST закрыть строку без отправки.

## Conformance
Реализация конформна, когда выполняет поведения 1-9, держит инварианты и правила отказов 1-3. Проверяется тестами tests/notifications/.