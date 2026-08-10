---
title: "Data model: iam"
status: accepted
tags:
  - "architecture"
  - "data-model"
  - "domain:iam"
---

SQLAlchemy schema · 2 entities.

| Entity | Key relations |
|--------|---------------|
| User (users) | 1:N UserSession (логическая, по user_id) |
| UserSession (user_sessions) | N:1 User via user_id (без FK-констрейнта) |

Relations: user_sessions.user_id ссылается на users.id логически, FK-констрейнт отсутствует.

## Индексы

| Индекс | Колонки | Обслуживает |
|--------|---------|-------------|
| ix_user_sessions_sid_hash (UNIQUE) | sid_hash | поиск сессии на каждом авторизованном запросе |
| ix_user_sessions_user_id_last_used | user_id, last_used | подрезка лимита сессий пользователя, логаут со всех устройств |

Поиск по номеру телефона и по telegram_id покрыт уникальными констрейнтами колонок.

Чистка простаивающих сессий по last_used идёт полным сканом намеренно: запрос
удаляет значимую долю таблицы, и на такой селективности индекс проигрывает
последовательному чтению.