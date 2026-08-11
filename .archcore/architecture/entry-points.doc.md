---
title: "Entry-point inventory"
status: accepted
tags:
  - "architecture"
  - "entry-points"
---

HTTP-сервер: `uvicorn app.main:app` (Dockerfile CMD, `./run.sh`). 57 роутов + /metrics.

### domain:iam
- @app/iam/router.py - HTTP. /api/auth (Telegram Login, сессии) + /api/users - 10 роутов.

### domain:threads
- @app/threads/router.py - HTTP. /api/threads + роуты комментариев и лайков - 11 роутов.

### domain:bookclubs
- @app/bookclubs/router.py - HTTP. /api/bookclubs (клубы, участие, приватность и роли, приглашения, заявки, жанры клуба, заходы и голосование за следующую книгу) - 25 роутов; /api/readings (прогресс и закрытие захода) - 3 роута; /api/nominations (голос за номинацию) - 2 роута.

### domain:genres
- @app/genres/router.py - HTTP. /api/genres (каталог жанров) - 4 роута.

### domain:books
- @app/books/router.py - HTTP. /api/books (поиск Google Books, ручное создание) - 2 роута.

### Прочее
- @app/main.py - HTTP. GET /metrics (Authorization: Bearer METRICS_TOKEN).
- @app/core/events.py - Worker. RabbitMQ consumer: одна очередь на домен, диспетчеризация по routing_key; старт в lifespan.
- docker-compose `cleanup` - Cron. Ежедневно 03:00 `python -m app.iam.tasks`.
- docker-compose `migrate` - Other. `alembic upgrade head` перед стартом app.
