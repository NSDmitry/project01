---
title: "Threads service: треды, комментарии, лайки"
status: accepted
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
- Кросс-доменные зависимости - только порты `ClubsPort`, `BooksPort`, `ReadingsPort`, `UsersPort` (@app/threads/ports.py) и события @app/core/events.py; авторство - `Principal` из @app/core/contracts.py.

## Normative Behavior
1. WHEN создаётся тред или комментарий, сервис MUST проверить членство автора в клубе через `ClubsPort.is_member`; лайк - аналогично по клубу треда.
2. WHEN тред создаётся с `book_volume_id`, сервис MUST получить или создать книгу через `BooksPort.get_or_create_book` и привязать её id.
3. WHEN тред создан, сервис MUST опубликовать THREAD_CREATED с `club_id`; WHEN тред удалён - THREAD_DELETED с `club_id` и `count` (счётчик тредов ведёт домен клубов).
4. Удалять тред MUST только автор; изменять тред MAY автор или владелец клуба (`require_permission`, @app/core/authorization.py).
5. Редактировать комментарий MUST только автор; удалять комментарий MAY автор или владелец клуба.
6. `like_comment`/`unlike_comment` MUST быть идемпотентны: повторный лайк и снятие отсутствующего лайка не являются ошибкой.
7. WHEN собирается ответ, сервис MUST подтягивать авторов батчем через `UsersPort.get_summaries_by_ids` (author_id - логическая ссылка, relationship в модели нет) и заполнять `likes_count`/`is_liked` явно.
8. WHEN `get_comments` вызван без пользователя, сервис MUST вернуть `is_liked = false` для всех комментариев.
9. `total` страницы тредов MUST браться из `threads_count` уже загруженного клуба, `total` страницы комментариев - из `comments_count` уже загруженного треда. Сервис MUST NOT запрашивать агрегат: он растёт с размером ленты, а не страницы, и на горячих тредах стоил дороже самой выборки.
10. WHEN тред создаётся с этапом захода, сервис MUST через `ReadingsPort.get_stage_club_id` убедиться, что этап принадлежит тому же клубу, и только тогда привязывать его. Проверка MUST идти до создания книги и треда.
11. WHEN лента тредов запрошена с фильтром по этапу, `total` MUST считаться запросом, а не браться из `threads_count` клуба: денормализованный счётчик считает все треды клуба и с фильтром неверен.

## Constraints & Invariants
- Инвариант: сервис не импортирует модули bookclubs/iam/books напрямую - только порты и события (санкционированное исключение - identity-провайдер в роутере).
- Инвариант: пагинация - `Page(items, total, limit, offset)`; треды - новые сверху, комментарии - старые сверху, лайкеры - свежие сверху.
- Инвариант: `total` тредов наследует точность `threads_count`, который ведётся событиями и при потере события может разъехаться; `total` комментариев ведётся в одной транзакции с комментарием и такого допуска не имеет.
- Инвариант: этап захода тред хранит идентификатором, без FK и без загрузки самого этапа - его содержимое отдаёт домен клубов.

## Failure Behavior
1. IF клуб, тред или комментарий не найден, THEN сервис MUST пробросить NotFound из порта/репозитория.
2. IF автор не участник клуба, THEN create/like MUST выбросить Forbidden.
3. IF пользователь не автор (и не владелец клуба, где это разрешено), THEN update/delete MUST выбросить Forbidden.
4. IF `author_id` треда/комментария NULL (автор удалён), THEN сервис MUST вернуть `author = null`, не ошибку.
5. IF этап не найден или принадлежит другому клубу, THEN `create_thread` MUST выбросить NotFound, а тред MUST NOT быть создан.

## Conformance
Реализация конформна, когда выполняет поведения 1-11, держит инварианты портов и пагинации и правила отказов 1-5. Проверяется тестами tests/threads/ и tests/comments/.
