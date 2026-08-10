---
title: "Threads HTTP API: /api/threads и /api/comments"
status: accepted
tags:
  - "domain:threads"
  - "spec"
  - "threads"
---

## Purpose & Scope
HTTP-контракт домена threads (@app/threads/router.py): роуты тредов и комментариев с лайками. Потребители - клиенты API. Вне scope: бизнес-правила (спек сервиса).

## Surface
- `/api/threads`: GET `/{club_id}` (страница тредов), POST `` (201), PUT `/{thread_id}`, DELETE `/{thread_id}`.
- Комментарии: GET/POST `/api/threads/{thread_id}/comments`, PUT/DELETE `/api/comments/{comment_id}`, GET `/api/comments/{comment_id}/likes`, POST/DELETE `/api/comments/{comment_id}/like`.
- Конверт `ResponseModel`, страницы `Page`; id в путях - `PathId` (границы BIGINT), смещение - `PageOffset` (@app/core/params.py).

## Normative Behavior
1. Мутации (POST/PUT/DELETE) MUST требовать `X-Session-Id` (`Depends(get_current_user)`).
2. GET-роуты (треды, комментарии, лайкеры) MUST работать без авторизации.
3. WHEN GET comments вызван с валидным `X-Session-Id`, роутер MUST рассчитать `is_liked` для текущего пользователя (`get_optional_user`).
4. Пагинация MUST принимать `limit` 1-100 (default 10) и `offset` в диапазоне 0..`MAX_OFFSET` (default 0). Потолок смещения общий для всех списочных ручек проекта и задан одной константой.
5. WHEN тред или комментарий создан, роутер MUST вернуть 201 с данными в `data`.
6. POST/DELETE `/like` MUST возвращать комментарий с актуальными `likes_count` и `is_liked`.

## Constraints & Invariants
- Инвариант: единственный кросс-доменный импорт роутера - identity-провайдер `app.iam.deps` (санкционированный seam, см. комментарий в файле).
- Ограничение: rate limiting на роутах threads отсутствует - только на IAM.

## Failure Behavior
1. IF id вне границ BIGINT или тело не проходит валидацию, THEN роутер MUST вернуть 422.
2. IF клуб/тред/комментарий не найден, THEN роутер MUST вернуть 404.
3. IF пользователь не участник клуба или не имеет прав, THEN роутер MUST вернуть 403 с причиной в `errors`.
4. IF `X-Session-Id` отсутствует или невалиден на мутации, THEN роутер MUST вернуть 401.
5. IF Google Books недоступен при создании треда с `book_volume_id`, THEN роутер MUST вернуть 503.
6. IF `offset` превышает потолок, THEN роутер MUST вернуть 422, а не обслуживать запрос. Глубокое смещение на длинной ленте комментариев заставляет БД собрать и отсортировать всё до страницы; живому клиенту такие страницы недостижимы. Снять потолок можно только вместе с переходом на курсорную пагинацию.

## Conformance
Реализация конформна, когда выполняет поведения 1-6 и правила отказов 1-6; коды задекларированы в `responses` роутов и проверяются тестами tests/threads/ и tests/comments/.
