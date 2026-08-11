---
title: "Top-level domain map"
status: accepted
tags:
  - "architecture"
  - "domain:bookclubs"
  - "domain:books"
  - "domain:iam"
  - "domain:notifications"
  - "domain:threads"
  - "top-level-map"
---

Корень `app/` · 6 доменов + общий слой `core`.

| Домен | Путь | Файлы | LOC | Описание |
|---|---|---|---|---|
| iam | app/iam | 11 | 1093 | Аутентификация (Telegram Login), серверные сессии, пользователи, аватар, настройки уведомлений. |
| threads | app/threads | 9 | 1047 | Треды, комментарии, лайки комментариев. |
| bookclubs | app/bookclubs | 9 | 808 | Книжные клубы, участники, жанры клуба, обложка. |
| books | app/books | 8 | 263 | Книги, поиск в Google Books, ручное создание. |
| genres | app/genres | 7 | 295 | Каталог жанров. |
| notifications | app/notifications | 6 | ~230 | Уведомления: outbox-очередь в Postgres, воркер доставки (cron), канал Telegram. Роутера нет - настройки в IAM. |

Общий слой: `app/core` - контракты между доменами (contracts.py), хранилище и обработка загруженных картинок (media.py), иерархия ошибок, rate limiting, базовые модели ответов.