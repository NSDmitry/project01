# Структура проекта

```text
app/
  core/            инфраструктура (БД, ошибки, общие схемы) + кросс-доменные контракты (contracts.py)
  iam/             домен идентичности: пользователи, сессии, аутентификация
  genres/          справочник жанров: публичный список, админский CRUD
  books/           книги: каталог + поиск через Google Books
  bookclubs/       домен книжных клубов: клубы, членство, жанры клуба
  threads/         домен обсуждений: треды и комментарии
  notifications/   уведомления: outbox-очередь в Postgres, relay в notification-service
migrations/        Alembic-миграции
notification_service/  отдельный сервис доставки уведомлений: приём батчей, очередь deliveries,
                   каналы, воркер; свои pyproject, Dockerfile, alembic и БД
tests/             интеграционные и API-тесты монолита
```

Каждый домен устроен одинаково: `router.py` (HTTP-роуты), `service.py` (бизнес-логика), `repository.py` (работа с базой), `models.py` (SQLAlchemy-модели), `schemas.py` (Pydantic-схемы), `deps.py` (FastAPI-зависимости).

Слои: router -> service -> repository. HTTP и авторизация - в роутере/сервисе, SQL - в репозитории.

Кросс-доменное взаимодействие - прямой вызов: сервис получает репозиторий/сервис соседнего домена через свой `deps.py` и вызывает его напрямую. Общие DTO (`UserSummary`, `GenreResponse`, `BookResponse`) и `Principal` (минимальная личность вызвавшего: `id`, `is_admin`) живут в `core.contracts`; авторизация в роутерах - через `iam.deps.get_current_user`/`get_optional_user`.

Уведомления - без брокера: outbox в монолите плюс отдельный сервис доставки. Событие (комментарий в треде, старт захода) кладёт строку в таблицу `notifications` в своей же транзакции. Relay `python -m app.notifications.tasks` (в docker-compose - сервис `notifier`, раз в минуту) генерирует напоминания о завтрашних дедлайнах (идемпотентно через `dedup_key`), фильтрует получателей (отключённые типы - `PUT /api/users/notification-settings`, отсутствие привязки Telegram) и передаёт готовые уведомления батчем в notification-service (`POST /v1/notifications:batch`, заголовок `X-Internal-Token`); строки outbox закрываются только после `202`, поэтому недоступность сервиса ничего не теряет. Сервис складывает батч в свою таблицу `deliveries` (повтор батча гасится UNIQUE `event_id`), его воркер `python -m service.worker` доставляет по каналам с лимитом попыток. Канал - функция `(chat-реквизиты, text)` в `notification_service/service/channels.py`; сейчас Telegram, новый провайдер (email/sms) - ещё одна функция плюс строка в `CHANNELS` в `worker.py`, релизом сервиса без релиза монолита. Кросс-импорты между `app/` и `notification_service/` запрещены - граница только HTTP.

Один HTTP-запрос - одна транзакция (граница - `get_db`, commit на успехе). Каскады удаления (пользователь, клуб, жанр) выполняются в этой же транзакции, атомарно: целостность связей держат настоящие FOREIGN KEY с ON DELETE CASCADE/SET NULL, за кодом остаются только денормализованные счётчики (напр. `book_clubs.threads_count` - прямым вызовом в транзакции создания/удаления треда) и развилки по флагам запроса.

## Наблюдаемость

Приложение экспортирует метрики на:

```text
/metrics
```

Метрики собираются через `prometheus-fastapi-instrumentator`.
