---
title: "Threads service: треды, комментарии, лайки"
status: draft
tags:
  - "domain:threads"
  - "spec"
  - "threads"
---

## Purpose & Scope
Контракт бизнес-логики домена threads: `ThreadService`, `CommentService` (@app/threads/service.py). Потребители - @app/threads/router.py и обработчики событий. Вне scope: HTTP-коды (спек роутера), SQL (спек репозитория).

## Surface
- `ThreadService`: `get_threads`, `create_thread`, `update_thread`, `delete_thread`.
- `CommentService`: `get_comments`, `get_comment_likers`, `create_comment`, `update_comment`, `delete_comment`, `like_comment`, `unlike_comment`.
- Кросс-доменные зависимости - только порты `ClubsPort`, `BooksPort`, `UsersPort` (@app/threads/ports.py) и события @app/core/events.py; авторство - `Principal` из @app/core/contracts.py.

## Normative Behavior
1. WHEN создаётся тред или комментарий, сервис MUST проверить членство автора в клубе через `ClubsPort.is_member`; лайк - аналогично по клубу треда.
2. WHEN тред создаётся с `book_volume_id`, сервис MUST получить или создать книгу через `BooksPort.get_or_create_book` и привязать её id.
3. WHEN тред создан, сервис MUST опубликовать THREAD_CREATED с `club_id`; WHEN тред удалён - THREAD_DELETED с `club_id` и `count` (счётчик тредов ведёт домен клубов).
4. Удалять тред MUST только автор; изменять тред MAY автор или владелец клуба (`require_permission`, @app/core/authorization.py).
5. Редактировать комментарий MUST только автор; удалять комментарий MAY автор или владелец клуба.
6. `like_comment`/`unlike_comment` MUST быть идемпотентны: повторный лайк и снятие отсутствующего лайка не являются ошибкой.
7. WHEN собирается ответ, сервис MUST подтягивать авторов батчем через `UsersPort.get_summaries_by_ids` (author_id - логическая ссылка, relationship в модели нет) и заполнять `likes_count`/`is_liked` явно.
8. WHEN `get_comments` вызван без пользователя, сервис MUST вернуть `is_liked = false` для всех комментариев.

## Constraints & Invariants
- Инвариант: сервис не импортирует модули bookclubs/iam/books напрямую - только порты и события (санкционированное исключение - identity-провайдер в роутере).
- Инвариант: пагинация - `Page(items, total, limit, offset)`; треды - новые сверху, комментарии - старые сверху, лайкеры - свежие сверху.

## Failure Behavior
1. IF клуб, тред или комментарий не найден, THEN сервис MUST пробросить NotFound из порта/репозитория.
2. IF автор не участник клуба, THEN create/like MUST выбросить Forbidden.
3. IF пользователь не автор (и не владелец клуба, где это разрешено), THEN update/delete MUST выбросить Forbidden.
4. IF `author_id` треда/комментария NULL (автор удалён), THEN сервис MUST вернуть `author = null`, не ошибку.

## Conformance
Реализация конформна, когда выполняет поведения 1-8, держит инварианты портов и пагинации и правила отказов 1-4. Проверяется тестами tests/threads/ и tests/comments/.