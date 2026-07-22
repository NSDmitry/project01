---
title: "Genres HTTP API: /api/genres"
status: accepted
tags:
  - "domain:genres"
  - "genres"
  - "spec"
---

## Purpose & Scope
HTTP-контракт справочника жанров (@app/genres/router.py). Потребители - клиенты API (чтение) и администраторы (CRUD). Вне scope: использование жанров клубами (спеки bookclubs).

## Surface
- GET `` (список), POST `` (201, создание), PUT `/{genre_id}`, DELETE `/{genre_id}`.
- Конверт `ResponseModel`; id - `PathId`.

## Normative Behavior
1. GET MUST работать без авторизации и возвращать справочник жанров.
2. Мутации (POST/PUT/DELETE) MUST требовать `X-Session-Id` и права администратора.
3. PUT MUST заменять код, название и порядок сортировки жанра целиком.
4. WHEN жанр создан, роутер MUST вернуть 201.

## Constraints & Invariants
- Инвариант: код жанра уникален.
- Инвариант: единственный кросс-доменный импорт - identity-провайдер `app.iam.deps`.

## Failure Behavior
1. IF пользователь не администратор, THEN мутация MUST вернуть 403.
2. IF жанр не найден, THEN PUT/DELETE MUST вернуть 404.
3. IF код жанра занят, THEN POST/PUT MUST вернуть 409.
4. IF код не проходит валидацию (паттерн слага), THEN роутер MUST вернуть 422.

## Conformance
Реализация конформна, когда выполняет поведения 1-4 и правила отказов 1-4; коды задекларированы в `responses` роутов, проверяются тестами tests/genres/.