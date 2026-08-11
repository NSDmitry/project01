---
title: "IAM repository: доступ к users и user_sessions"
status: accepted
tags:
  - "domain:iam"
  - "iam"
  - "spec"
---

## Purpose & Scope
Контракт слоя хранения IAM: `UserRepository` и `UserSessionRepository` (@app/iam/repository.py). Потребители - @app/iam/service.py, @app/iam/deps.py и `get_summaries_by_ids` - кросс-доменный порт для threads через @app/core/contracts.py. Вне scope: бизнес-правила и хеширование (спек сервиса).

## Surface
- `UserRepository`: `get_user_by_id`, `get_summaries_by_ids`, `get_user_by_phone_number`, `get_user_by_telegram_id`, `create_user`, `create_telegram_user`, `update_user_info`, `update_avatar`, `update_user_password`, `delete_user`.
- `UserSessionRepository`: `create_user_session`, `get_user_session`, `update_last_used`, `delete_user_session`, `delete_all_user_sessions`, `delete_sessions_over_limit`, `delete_idle_sessions`.
- Модели: `User` (users), `UserSession` (user_sessions) - @app/iam/models.py.

## Normative Behavior
1. WHEN `get_user_by_id` не находит пользователя, репозиторий MUST выбросить NotFound.
2. `get_summaries_by_ids` MUST возвращать результат в порядке `User.id`, а не в порядке входного списка; на пустой список MUST вернуть пустой список без запроса к БД.
3. WHEN `create_telegram_user` ловит IntegrityError (параллельный первый вход уже создал запись), репозиторий MUST откатить транзакцию и вернуть существующего пользователя.
4. WHEN `create_user` или `update_user_info` ловит IntegrityError по номеру телефона (гонка после проверки уникальности), репозиторий MUST откатить и выбросить Conflict.
5. `delete_sessions_over_limit` MUST оставить `keep` самых свежих по `last_used` сессий пользователя и удалить остальные.
6. `delete_idle_sessions` MUST удалить сессии с `last_used` старше cutoff или NULL и вернуть число удалённых строк.
7. `update_avatar` MUST записать в `users.avatar_key` ключ файла в хранилище картинок и вернуть обновлённого пользователя; сам файл репозиторий не трогает.
8. Репозиторий MUST завершать записи `flush`, а не `commit` - границы транзакции держит вызывающий слой (session dependency).

## Constraints & Invariants
- Инвариант: `user_sessions.user_id` - настоящий FK на users с ON DELETE CASCADE: сессии удалённого пользователя уносит БД. `delete_all_user_sessions` остаётся для логаута со всех устройств; его вызов при удалении аккаунта - безвредная повторная чистка.
- Инвариант: `delete_user` не трогает данные других доменов кодом - строки с FK на users уносит или обнуляет ON DELETE, а развилки по флагам удаления и счётчики отрабатывают обработчики события USER_DELETED (до завершения эпика #75).
- Инвариант: в БД лежит только ключ файла (`avatar_key`), не URL - ссылка собирается из ключа при формировании ответа, и переезд хранилища не требует переписывания строк.

## Failure Behavior
1. IF поиск по phone_number/telegram_id/sid_hash не нашёл строку, THEN метод MUST вернуть None (не исключение); исключение NotFound - только у `get_user_by_id`.
2. IF `create_user` падает не-IntegrityError-исключением, THEN репозиторий MUST откатить транзакцию и выбросить InternalServerError.
3. IF `delete_user_session` не находит сессию, THEN метод MUST завершиться без ошибки (идемпотентный logout).

## Conformance
Реализация конформна, когда выполняет поведения 1-8 и правила отказов 1-3; порядок `get_summaries_by_ids` и гонки создания проверяются тестами tests/sso_tests/test_register_atomicity.py и tests/comments/.