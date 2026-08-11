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
| User (users) | 1:N UserSession (FK CASCADE), 1:N Notification (домен notifications, FK CASCADE) |
| UserSession (user_sessions) | N:1 User via user_id (FK, ON DELETE CASCADE) |

Relations: user_sessions.user_id - настоящий FK на users.id с ON DELETE CASCADE: сессии удалённого пользователя уносит БД. Тем же способом (FK CASCADE) с users связана очередь notifications соседнего домена уведомлений.

Аватар: `users.avatar_key` - ключ файла в хранилище картинок (`avatars/<uuid>.webp`), NULL - аватара нет. В БД лежит ключ, а не URL: ссылка собирается при формировании ответа, и переезд хранилища не требует переписывания строк. Сам файл вне базы, удаляется кодом вместе с аккаунтом (см. @.archcore/architecture/core-media.spec.md).

Настройки уведомлений: `users.disabled_notifications` - ARRAY(String) NOT NULL DEFAULT '{}' с отключёнными пользователем типами уведомлений (значения `NotificationType` из @app/notifications/models.py). По умолчанию пусто - все типы включены. Массив на строке пользователя, а не отдельная таблица: воркер доставки и так загружает строку пользователя ради `telegram_id` и получает фильтр без единого лишнего запроса.

## Индексы

| Индекс | Колонки | Обслуживает |
|--------|---------|-------------|
| ix_user_sessions_sid_hash (UNIQUE) | sid_hash | поиск сессии на каждом авторизованном запросе |
| ix_user_sessions_user_id_last_used | user_id, last_used | подрезка лимита сессий пользователя, логаут со всех устройств, каскад при удалении пользователя (user_id - префикс) |

Поиск по номеру телефона и по telegram_id покрыт уникальными констрейнтами колонок.
Аватар по индексу не ищется - ключ читается только вместе со строкой пользователя.
disabled_notifications по индексу не ищется - массив читается вместе со строкой пользователя.

Чистка простаивающих сессий по last_used идёт полным сканом намеренно: запрос
удаляет значимую долю таблицы, и на такой селективности индекс проигрывает
последовательному чтению.