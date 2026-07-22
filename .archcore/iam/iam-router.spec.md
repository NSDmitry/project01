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
- `/api/users`: GET `/current`, GET `/public?user_id=`, PUT `` (имя и номер), PUT `/password`, DELETE `/current`.
- Все ответы - конверт `ResponseModel` (@app/core/models/response_model.py): `data`, `message`, `errors`.
- Авторизация - заголовок `X-Session-Id` через `Depends(get_current_user)` (@app/iam/deps.py).

## Normative Behavior
1. WHEN клиент вызывает POST /register с валидными данными, роутер MUST вернуть 201 и `session_id` в `data`.
2. Роутер MUST применять rate limit: /register и /login - 5 запросов в 60 с, /login-available и /telegram - 10 в 60 с, PUT /password - 5 в 60 с.
3. Роуты /api/users/* MUST требовать валидную сессию `X-Session-Id`; /api/auth/* (кроме /logout) MUST быть доступны без сессии.
4. WHEN клиент вызывает GET /public с `user_id`, роутер MUST валидировать его как QueryId (границы BIGINT, @app/core/params.py).
5. WHEN клиент вызывает DELETE /current, роутер MUST принять флаги `delete_clubs`/`delete_threads`/`delete_comments` (default false) и `password` в теле; false - контент отвязывается (owner/author -> null), true - удаляется.
6. WHEN операция успешна, роутер MUST вернуть данные в конверте `ResponseModel` с `errors = []`.

## Constraints & Invariants
- Инвариант: ни один хендлер не ходит в репозитории напрямую - только через сервисы (`get_auth_service`, `get_user_service`).
- Ограничение: rate limiting задаётся на уровне роута через `rate_limiter(...)` (@app/core/rate_limit.py); в тестах без Redis деградирует в no-op.

## Failure Behavior
1. IF пароль не проходит policy, THEN роутер MUST вернуть 400.
2. IF номер или пароль неверны, THEN /login MUST вернуть 401 (без различения причин).
3. IF номер занят, THEN /register и PUT /api/users MUST вернуть 409.
4. IF превышен rate limit или номер заблокирован подбором, THEN роутер MUST вернуть 429.
5. IF `X-Session-Id` отсутствует, невалиден или сессия истекла, THEN защищённый роут MUST вернуть 401.
6. IF тело запроса не проходит pydantic-валидацию, THEN роутер MUST вернуть 422 (глобальный хендлер @app/main.py, поля с ошибками в `errors`).

## Conformance
Реализация конформна, когда выполняет поведения 1-6 и правила отказов 1-6; фактические коды задекларированы в `responses` каждого роута и проверяются тестами tests/sso_tests/ и tests/users/.