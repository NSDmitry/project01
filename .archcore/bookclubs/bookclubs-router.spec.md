---
title: "Bookclubs HTTP API: /api/bookclubs"
status: draft
tags:
  - "bookclubs"
  - "domain:bookclubs"
  - "spec"
---

## Purpose & Scope
HTTP-контракт домена bookclubs (@app/bookclubs/router.py): клубы, участие, жанры клуба, поиск. Потребители - клиенты API. Вне scope: бизнес-правила (спек сервиса).

## Surface
- POST `` (201, создание), GET `` (список постранично), POST `/search`, GET `/{club_id}`, GET `/{club_id}/members`, DELETE `/{club_id}`, POST `/{club_id}/join`, DELETE `/{club_id}/leave`, PUT `/{club_id}/genres`.
- Конверт `ResponseModel`, страницы `Page`; id - `PathId` (@app/core/params.py).

## Normative Behavior
1. Все роуты MUST требовать `X-Session-Id` (`Depends(get_current_user)`) - включая чтение.
2. WHEN клуб создан, роутер MUST вернуть 201; создатель автоматически становится владельцем и участником.
3. POST /search MUST принимать `query` (подстрока по названию, описанию, жанрам, регистронезависимо) и `relation` (`owner` - свои клубы, `member` - клубы, где состоит) - все поля необязательны.
4. PUT /genres MUST заменять набор жанров клуба присланным списком кодов (0-5) целиком; доступно только владельцу.
5. Пагинация MUST принимать `limit` 1-100 (default 20) и `offset` >= 0.

## Constraints & Invariants
- Инвариант: единственный кросс-доменный импорт - identity-провайдер `app.iam.deps` (санкционированный seam).

## Failure Behavior
1. IF имя клуба занято, THEN POST MUST вернуть 409.
2. IF пользователь уже участник (join) или не участник (leave), THEN роутер MUST вернуть 409.
3. IF пользователь не владелец (delete, genres), THEN роутер MUST вернуть 403.
4. IF клуб не найден, THEN роутер MUST вернуть 404.
5. IF жанр из списка неизвестен, THEN PUT /genres MUST вернуть 422 с перечнем неизвестных кодов в `errors`.

## Conformance
Реализация конформна, когда выполняет поведения 1-5 и правила отказов 1-5; коды задекларированы в `responses` роутов, проверяются тестами tests/bookclubs/.