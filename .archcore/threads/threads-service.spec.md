---
title: "Threads service: треды, комментарии, лайки"
status: accepted
tags:
  - "domain:threads"
  - "spec"
  - "threads"
---

## Purpose & Scope
Контракт бизнес-логики домена threads: `ThreadService`, `CommentService` (@app/threads/service.py). Потребители - @app/threads/router.py. Вне scope: HTTP-коды (спек роутера), SQL (спек репозитория).

## Surface
- `ThreadService`: `get_threads`, `create_thread`, `update_thread`, `delete_thread`.
- `CommentService`: `get_comments`, `get_comment_likers`, `create_comment`, `update_comment`, `delete_comment`, `like_comment`, `unlike_comment`.
- Кросс-доменные зависимости - конкретные классы соседних доменов через deps.py (`BookClubRepository`, `ReadingRepository`, `BookService`, `UserRepository`, `NotificationRepository`); авторство - `Principal` из @app/core/contracts.py.

## Normative Behavior
1. WHEN создаётся тред или комментарий, сервис MUST проверить членство автора в клубе через `BookClubRepository.is_member`; лайк - аналогично по клубу треда.
2. WHEN тред создаётся с `book_volume_id`, сервис MUST получить или создать книгу через `BookService.get_or_create_book` и привязать её id.
3. WHEN тред создан или удалён, сервис MUST в той же транзакции поправить счётчик тредов клуба прямым вызовом `BookClubRepository.change_threads_count` (+1/-1). События для счётчика MUST NOT публиковаться.
4. Удалять тред MUST только автор; изменять тред MAY автор или владелец клуба (`require_permission`, @app/core/authorization.py).
5. Редактировать комментарий MUST только автор; удалять комментарий MAY автор или владелец клуба.
6. `like_comment`/`unlike_comment` MUST быть идемпотентны: повторный лайк и снятие отсутствующего лайка не являются ошибкой.
7. WHEN собирается ответ, сервис MUST подтягивать авторов батчем через `UserRepository.get_summaries_by_ids` (relationship на пользователя в модели нет) и заполнять `likes_count`/`is_liked` явно.
8. WHEN `get_comments` вызван без пользователя, сервис MUST вернуть `is_liked = false` для всех комментариев.
9. `total` страницы тредов MUST браться из `threads_count` уже загруженного клуба, `total` страницы комментариев - из `comments_count` уже загруженного треда. Сервис MUST NOT запрашивать агрегат: он растёт с размером ленты, а не страницы, и на горячих тредах стоил дороже самой выборки.
10. WHEN тред создаётся с этапом захода, сервис MUST через `ReadingRepository.get_stage_club_id` убедиться, что этап принадлежит тому же клубу, и только тогда привязывать его. Проверка MUST идти до создания книги и треда.
11. WHEN лента тредов запрошена с фильтром по этапу, `total` MUST считаться запросом, а не браться из `threads_count` клуба: денормализованный счётчик считает все треды клуба и с фильтром неверен.
12. WHEN комментарий создан, сервис MUST в той же транзакции положить автору треда уведомление `comment_in_thread` через `NotificationRepository.add` (outbox, см. @.archcore/notifications/notifications.spec.md). Уведомление MUST NOT создаваться, если комментатор сам автор треда или `author_id` треда NULL (автор удалён).

## Constraints & Invariants
- Инвариант: сервис получает соседние домены только через deps.py - конкретными классами, без портов и без публикации событий (санкционированное исключение - identity-провайдер в роутере).
- Инвариант: пагинация - `Page(items, total, limit, offset)`; треды - новые сверху, комментарии - старые сверху, лайкеры - свежие сверху.
- Инвариант: `threads_count` клуба правится в одной транзакции с созданием/удалением треда, как и `comments_count` с комментарием - допуска на расхождение из-за потерянного события больше нет.
- Инвариант: этап захода тред хранит идентификатором (FK с ON DELETE SET NULL) и не загружает сам этап - его содержимое отдаёт домен клубов.

## Failure Behavior
1. IF клуб, тред или комментарий не найден, THEN сервис MUST пробросить NotFound из репозитория.
2. IF автор не участник клуба, THEN create/like MUST выбросить Forbidden.
3. IF пользователь не автор (и не владелец клуба, где это разрешено), THEN update/delete MUST выбросить Forbidden.
4. IF `author_id` треда/комментария NULL (автор удалён), THEN сервис MUST вернуть `author = null`, не ошибку.
5. IF этап не найден или принадлежит другому клубу, THEN `create_thread` MUST выбросить NotFound, а тред MUST NOT быть создан.

## Conformance
Реализация конформна, когда выполняет поведения 1-12, держит инварианты зависимостей и пагинации и правила отказов 1-5. Проверяется тестами tests/threads/, tests/comments/ и tests/notifications/test_notification_outbox.py.