---
title: "External integrations"
status: accepted
tags:
  - "architecture"
  - "integrations"
---

## Data stores
- Redis - via `redis` + `fastapi-limiter`. Держит две разные вещи: rate limiting IAM-эндпоинтов и лимит регистраций с IP (@app/core/rate_limit.py), а также эскалирующие блокировки подбора пароля по номеру телефона и по IP (@app/iam/brute_force.py).
- Redis на критическом пути входа: если он сконфигурирован, но недоступен, `/api/auth/login` завершается ошибкой 500. Деградация в no-op работает только для случая "не сконфигурирован" (тесты).
- S3-совместимое хранилище - via `boto3`, обложки клубов и аватары пользователей (@app/core/media.py). MinIO в docker-compose, Object Storage в проде. Пустой S3_ENDPOINT_URL = запись в локальный каталог (тесты, запуск без бакета). Бакет приватный: наружу картинки раздаёт приложение по `GET /media/<ключ>`, ссылок на хранилище клиент не получает.

## External APIs
- Telegram - Telegram Login, проверка подписи входа по TELEGRAM_BOT_TOKEN (@app/iam/security).
- Google Books - поиск книг через httpx-клиент (@app/books/google_client.py). Обложки книг приходят готовыми ссылками оттуда и в наше хранилище не попадают.