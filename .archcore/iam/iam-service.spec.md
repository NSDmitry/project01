---
title: "IAM service: аутентификация, сессии, пользователи"
status: accepted
tags:
  - "domain:iam"
  - "iam"
  - "spec"
---

## Purpose & Scope
Нормативный контракт бизнес-логики IAM: `AuthService`, `UserService`, `UserSessionService` (@app/iam/service.py). Потребители - @app/iam/router.py, @app/iam/deps.py (авторизация всех остальных доменов) и @app/iam/tasks.py (cron-очистка). Вне scope: HTTP-коды и rate limiting (спек роутера), SQL-слой (спек репозитория).

## Surface
- `AuthService`: `register`, `login`, `check_login_available`, `login_with_telegram`, `logout`, `change_password`, `delete_current_user`, `validate_password_policy` - @app/iam/service.py.
- `UserSessionService`: `create_user_session`, `get_user_session`, `logout_user_session`, `logout_all_user_sessions`, `cleanup_idle_sessions`.
- `UserService`: `get_user_by_id`, `update_user_info`, `validate_phone_number`.
- Константы: `MAX_SESSIONS_PER_USER = 5`, `SESSION_MAX_IDLE = 30 дней`, `LAST_USED_THRESHOLD = 5 минут`.
- Зависимости: эскалирующая блокировка @app/iam/brute_force.py, подпись Telegram @app/iam/security/telegram.py, событийная шина @app/core/events.py.

## Normative Behavior
1. WHEN вызывается `register`, сервис MUST проверить лимит регистраций с IP до создания пользователя (@app/core/rate_limit.py).
2. WHEN вызывается `register` или `change_password`, сервис MUST проверить пароль по policy: длина 8-128, хотя бы одна заглавная, одна строчная, одна цифра, без ведущих/замыкающих пробелов.
3. Сервис MUST хешировать пароль bcrypt в отдельном потоке (`asyncio.to_thread`) - bcrypt блокирует event loop.
4. WHEN `login` получает несуществующий номер или неверный пароль, сервис MUST вернуть один и тот же ответ Unauthorized (анти-enumeration).
5. WHEN попытка входа неудачна, сервис MUST зарегистрировать её в эскалирующей блокировке; WHEN вход успешен, сервис MUST сбросить счётчики блокировки.
6. WHEN вызывается `login_with_telegram`, сервис MUST проверить HMAC-подпись initData и возраст `auth_date` (не старше 1 часа) до обращения к БД.
7. WHEN Telegram-пользователь входит впервые, сервис MUST создать запись User по `telegram_id` без пароля.
8. WHEN создаётся сессия, сервис MUST выдать `sid = secrets.token_urlsafe(32)` и сохранить только его SHA-256-хеш.
9. WHEN создаётся сессия сверх лимита 5 на пользователя, сервис MUST удалить самые старые сессии сверх лимита.
10. WHEN `get_user_session` находит сессию с `last_used` старше 5 минут, сервис MUST обновить `last_used`; чаще - MUST NOT (экономия записей).
11. WHEN вызывается `change_password`, сервис MUST подтвердить текущий пароль и завершить все активные сессии пользователя после смены.
12. WHEN вызывается `delete_current_user`, сервис MUST опубликовать событие USER_DELETED с флагами `delete_clubs`/`delete_threads`/`delete_comments` до удаления пользователя, затем удалить пользователя и все его сессии.

## Constraints & Invariants
- Инвариант: сырой `sid` нигде не сохраняется - в БД только SHA-256-хеш.
- Инвариант: у пользователя не больше 5 живых сессий.
- Инвариант: iam не импортирует модули bookclubs/threads - очистка чужих данных только через событие USER_DELETED.
- Ограничение: неудачные подтверждения пароля (change_password, delete) идут в ту же блокировку, что и login, - иначе украденная сессия позволяет перебирать пароль в обход блокировки.

## Failure Behavior
1. IF номер уже занят, THEN `register`/`update_user_info` MUST выбросить Conflict.
2. IF номер телефона заблокирован эскалацией (5 неудач: блок 60 с, далее 30 мин, далее 24 ч), THEN сервис MUST выбросить TooManyRequests с оставшимся TTL; попытки во время блока идут в счёт эскалации.
3. IF сессия не использовалась дольше 30 дней, THEN `get_user_session` MUST выбросить Unauthorized с errors=["session_expired"].
4. IF подпись Telegram неверна, отсутствует или initData старше 1 часа, THEN сервис MUST выбросить Unauthorized.
5. IF у аккаунта нет пароля (Telegram-only), THEN `change_password` MUST выбросить BadRequest, а `delete_current_user` MUST пропустить подтверждение пароля.
6. IF Redis недоступен (тесты), THEN блокировка и лимиты MUST деградировать в no-op, не ломая вход.

## Conformance
Реализация конформна, когда выполняет поведения 1-12, держит инварианты (хеш-only sid, лимит сессий, отсутствие импортов чужих доменов) и правила отказов 1-6. Проверяется тестами tests/sso_tests/ и tests/users/.