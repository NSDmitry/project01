---
title: "IAM HTTP API: /api/auth и /api/users"
status: accepted
tags:
  - "domain:iam"
  - "iam"
  - "spec"
---

## Purpose & Scope
HTTP-контракт IAM: роуты `/api/auth/*` и `/api/users/*` (@app/iam/router.py). Потребители - фронтенды (Telegram Mini App) и все клиенты API. Вне scope: бизнес-правила (спек сервиса), формат ошибок приложения (задаётся глобальными хендлерами @app/main.py).

## Surface
- `/api/auth`: POST `/register` (201), POST `/login`, POST `/login-available`, POST `/telegram`, POST `/logout`.
- `/api/users`: GET `/current`, GET `/public?user_id=`, PUT `` (имя и номер), PUT `/avatar` (multipart), PUT `/password`, GET `/notification-settings`, PUT `/notification-settings`, DELETE `/current`.
- Все ответы - конверт `ResponseModel` (@app/core/models/response_model.py): `data`, `message`, `errors`.
- Авторизация - заголовок `X-Session-Id` через `Depends(get_current_user)` (@app/iam/deps.py).

## Normative Behavior
1. WHEN клиент вызывает POST /register с валидными данными, роутер MUST вернуть 201 и `session_id` в `data`.
2. Роутер MUST применять rate limit: /register и /login - 5 запросов в 60 с, /login-available и /telegram - 10 в 60 с, PUT /password - 5 в 60 с, PUT /avatar - 10 в 60 с.
3. POST /register и POST /login MUST передавать в сервис IP клиента: первый заголовок `X-Forwarded-For` от reverse-proxy, иначе адрес пира (@app/core/rate_limit.py).
4. Роуты /api/users/* MUST требовать валидную сессию `X-Session-Id`; /api/auth/* (кроме /logout) MUST быть доступны без сессии.
5. WHEN клиент вызывает GET /public с `user_id`, роутер MUST валидировать его как QueryId (границы BIGINT, @app/core/params.py).
6. WHEN клиент вызывает DELETE /current, роутер MUST принять флаги `delete_clubs`/`delete_threads`/`delete_comments` (default false) и `password` в теле; false - контент отвязывается (owner/author -> null), true - удаляется.
7. WHEN клиент вызывает PUT /avatar с `multipart/form-data` и полем `file`, роутер MUST вернуть профиль текущего пользователя со ссылкой `avatar_url`; ограничения по типу и размеру задаёт @app/core/media.py.
8. Профиль в ответах MUST содержать `avatar_url` - относительный путь `/media/<ключ>` либо null, если аватар не загружен. Это касается и `GET /current`, и `GET /public` (контракт `UserSummary` в @app/core/contracts.py).
9. WHEN операция успешна, роутер MUST вернуть данные в конверте `ResponseModel` с `errors = []`.
10. GET /notification-settings MUST возвращать `disabled` - список отключённых пользователем типов уведомлений (значения `NotificationType` домена notifications). PUT /notification-settings MUST принимать полный список отключённых типов (replace-set, как жанры клуба): пустой список включает все уведомления; дубли в запросе MUST схлопываться.

## Constraints & Invariants
- Инвариант: ни один хендлер не ходит в репозитории напрямую - только через сервисы (`get_auth_service`, `get_user_service`).
- Ограничение: rate limiting задаётся на уровне роута через `rate_limiter(...)` (@app/core/rate_limit.py); в тестах без Redis деградирует в no-op.
- Ограничение: доверие к `X-Forwarded-For` держится на том, что приложение доступно только через reverse-proxy, который перезаписывает этот заголовок. Появление доверенных прокси перед ним (CDN) отдаёт ключ блокировки под контроль клиента.
- Ограничение: роутер не отдаёт байты аватара - за ними клиент идёт по `avatar_url` в общий роут раздачи картинок (@app/main.py).

## Failure Behavior
1. IF пароль не проходит policy, THEN роутер MUST вернуть 400.
2. IF номер или пароль неверны, THEN /login MUST вернуть 401 (без различения причин).
3. IF номер занят, THEN /register и PUT /api/users MUST вернуть 409.
4. IF превышен rate limit роута либо сработала блокировка подбора по номеру телефона или по IP, THEN роутер MUST вернуть 429, не различая в теле ответа причину блокировки.
5. IF `X-Session-Id` отсутствует, невалиден или сессия истекла, THEN защищённый роут MUST вернуть 401.
6. IF тело запроса не проходит pydantic-валидацию, THEN роутер MUST вернуть 422 (глобальный хендлер @app/main.py, поля с ошибками в `errors`). Неизвестный тип уведомления в PUT /notification-settings отклоняется этим же путём.
7. IF файл в PUT /avatar больше лимита, THEN роутер MUST вернуть 413; IF содержимое не изображение или формат не поддерживается, THEN 415.

## Conformance
Реализация конформна, когда выполняет поведения 1-10 и правила отказов 1-7; фактические коды задекларированы в `responses` каждого роута и проверяются тестами tests/sso_tests/, tests/users/, tests/media/test_image_uploads.py и tests/notifications/test_notification_settings.py.