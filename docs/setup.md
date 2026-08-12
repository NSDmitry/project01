# Запуск проекта

## Быстрый старт

### 1. Установить зависимости

Требуется `Python 3.11`.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Поднять PostgreSQL и Redis

Локальные база и Redis поднимаются через `docker-compose.yml`:

```bash
docker compose up -d db redis
```

Postgres слушает только на `127.0.0.1:5432` (наружу не торчит), Redis - во внутренней сети.

### 3. Создать `.env`

Скопировать шаблон и подставить свои значения (реальные секреты в git не коммитим):

```bash
cp .env.example .env
```

Ключевые переменные:
- `DATABASE_URL` - строка подключения к основной базе данных
- `ORIGIN_URLS` - список origin'ов для CORS
- `REDIS_URL` - Redis для rate limiting и блокировок при подборе пароля
- `TELEGRAM_BOT_TOKEN` - токен бота для входа через Telegram Mini App (утечка = подделка входа за любого пользователя)
- `GOOGLE_BOOKS_API_KEY` - ключ Google Books API для поиска книг; пусто = запросы без ключа (меньшие квоты)
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` - учётка Postgres для docker-compose
- `S3_ENDPOINT_URL` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET` - S3-хранилище картинок (обложки, аватары); пустой endpoint = файлы пишутся в локальный каталог `MEDIA_ROOT`, для локальной разработки MinIO не обязателен
- `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` - учётка MinIO для docker-compose
- `NOTIFICATION_SERVICE_URL` / `INTERNAL_TOKEN` - адрес notification-service и общий секрет приёма батчей; их использует relay уведомлений (см. [Структура проекта](architecture.md))
- `NOTIFICATIONS_POSTGRES_USER` / `NOTIFICATIONS_POSTGRES_PASSWORD` / `NOTIFICATIONS_POSTGRES_DB` - учётка отдельной БД notification-service для docker-compose
- `METRICS_TOKEN` - пусто = `/metrics` отключён; иначе доступ по `Authorization: Bearer <токен>`
- `DOCS_ENABLED` - `false` в проде скрывает Swagger/ReDoc/OpenAPI

### 4. Применить миграции

Схема базы управляется только `Alembic` - приложение не создаёт таблицы при старте, поэтому миграции нужно применить вручную:

```bash
alembic upgrade head
```

Подробнее - в [Миграции](migrations.md).

### 5. Запустить приложение

```bash
uvicorn app.main:app --reload --log-level debug
```

После запуска сервис будет доступен на [http://localhost:8000](http://localhost:8000).

## Запуск через Docker Compose

Если нужен запуск приложения и базы вместе:

```bash
docker compose up --build
```

Сервис приложения поднимается на `localhost:8000`, база данных на `localhost:5432`. Вместе с ними поднимаются:

- `cleanup` - раз в сутки в `03:00` чистит протухшие сессии;
- `notifier` - раз в минуту генерирует дедлайн-напоминания и передаёт очередь `notifications` батчем в notification-service (relay);
- `notifications-db`, `notification-migrate`, `notification-service`, `notification-worker` - отдельный сервис доставки уведомлений со своей БД: приём батчей и отправка в Telegram. Токен отправки `TELEGRAM_BOT_TOKEN` нужен воркеру; у монолита тот же токен остаётся только для входа через Telegram;
- `minio` (плюс разовый `minio-init`, создающий бакет) - S3-хранилище картинок;
- `caddy` - reverse-proxy с TLS (порты 80/443).
