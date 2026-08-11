---
title: "Configuration &amp; environment surface"
status: accepted
tags:
  - "architecture"
  - "config"
---

Source: `.env.example`.

## Database
- DATABASE_URL - строка подключения к Postgres (secret)
- POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB - учётка Postgres для docker-compose (secret)

## Auth & secrets
- TELEGRAM_BOT_TOKEN - токен бота, которым проверяется подпись Telegram Login (secret)
- METRICS_TOKEN - Bearer-токен доступа к /metrics; пусто = эндпоинт отключён (secret)

## External services
- REDIS_URL - Redis для rate limiting и блокировок подбора пароля; недоступный Redis ломает вход (500)
- RABBITMQ_URL - RabbitMQ для кросс-доменных событий; пусто = синхронная доставка in-process (secret)
- RABBITMQ_USER / RABBITMQ_PASSWORD - учётка RabbitMQ для docker-compose (secret)

## Media storage
- S3_ENDPOINT_URL - адрес S3-совместимого хранилища картинок (MinIO в compose, Object Storage в проде); пусто = файлы пишутся в локальный каталог MEDIA_ROOT
- S3_BUCKET - имя бакета под обложки клубов и аватары
- S3_ACCESS_KEY / S3_SECRET_KEY - ключ доступа к хранилищу (secret)
- S3_REGION - регион; MinIO игнорирует, Object Storage требует свой
- MEDIA_ROOT - каталог локального хранилища; работает только при пустом S3_ENDPOINT_URL (тесты, запуск без бакета)
- MINIO_ROOT_USER / MINIO_ROOT_PASSWORD - учётка MinIO для docker-compose, должна совпадать с S3_ACCESS_KEY/S3_SECRET_KEY (secret)

## Runtime
- ORIGIN_URLS - список origin'ов для CORS
- DOCS_ENABLED - false скрывает /docs, /redoc и /openapi.json
- DOMAIN - домен для Caddy, под него выпускается TLS-сертификат