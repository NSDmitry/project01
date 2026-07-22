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
- REDIS_URL - Redis для rate limiting
- RABBITMQ_URL - RabbitMQ для кросс-доменных событий; пусто = синхронная доставка in-process (secret)
- RABBITMQ_USER / RABBITMQ_PASSWORD - учётка RabbitMQ для docker-compose (secret)

## Runtime
- ORIGIN_URLS - список origin'ов для CORS
- DOCS_ENABLED - false скрывает /docs, /redoc и /openapi.json
- DOMAIN - домен для Caddy, под него выпускается TLS-сертификат