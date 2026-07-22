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
- Redis - via `redis` + `fastapi-limiter`. Держит две разные вещи: rate limiting IAM-эндпоинтов и лимит регистраций с IP (@app/core/rate_limit.py), а также эскалирующие блокировки подбора пароля по номеру телефона и по IP (@app/iam/brute_force.py).
- Redis на критическом пути входа: если он сконфигурирован, но недоступен, `/api/auth/login` завершается ошибкой 500. Деградация в no-op работает только для случая "не сконфигурирован" (тесты).

## External APIs
- Telegram - Telegram Login, проверка подписи входа по TELEGRAM_BOT_TOKEN (@app/iam/security).
- Google Books - поиск книг через httpx-клиент (@app/books/google_client.py).