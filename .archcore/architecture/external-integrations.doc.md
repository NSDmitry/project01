---
title: "External integrations"
status: accepted
tags:
  - "architecture"
  - "integrations"
---

## Messaging & Queue
- RabbitMQ - via `aio-pika`, кросс-доменные события; пустой RABBITMQ_URL = синхронная доставка in-process (@app/core/events.py).

## Data stores
- Redis - via `redis` + `fastapi-limiter`, rate limiting IAM-эндпоинтов (@app/core/rate_limit.py).

## External APIs
- Telegram - Telegram Login, проверка подписи входа по TELEGRAM_BOT_TOKEN (@app/iam/security).
- Google Books - поиск книг через httpx-клиент (@app/books/google_client.py).