---
title: "Threads repository: доступ к threads, comments, comment_likes"
status: accepted
tags:
  - "domain:threads"
  - "spec"
  - "threads"
---

## Purpose & Scope
Контракт слоя хранения threads: `ThreadRepository`, `CommentRepository` (@app/threads/repository.py). Потребители - @app/threads/service.py и `AuthService.delete_current_user` (@app/iam/service.py) через @app/iam/deps.py. Вне scope: проверки прав и членства (спек сервиса).

## Surface
- `ThreadRepository`: `get_threads`, `count_threads`, `get_thread`, `create_thread`, `update_thread`, `delete_thread`, `delete_user_content`.
- `CommentRepository`: `get_comments`, `get_comment`, `create_comment`, `update_comment`, `delete_comment`, `add_like`, `remove_like`, `get_likers`, `get_likes_counts`, `get_liked_comment_ids`.
- Модели: `Thread`, `Comment`, `CommentLike` - @app/threads/models.py.

## Normative Behavior
1. `get_threads` MUST сортировать по `created_at DESC, id DESC`; `get_comments` - по `created_at ASC, id ASC`; `get_likers` - по `created_at DESC, id DESC`.
2. `get_threads` и `get_comments` MUST возвращать только страницу элементов. Общее число репозиторий не считает: для тредов его держит `BookClub.threads_count`, для комментариев - `Thread.comments_count`, и родитель к моменту вызова уже загружен сервисом. `get_likers` MUST возвращать `(items, total)` - для лайков отдельного счётчика нет.
3. WHEN `get_thread`/`get_comment` не находит строку, репозиторий MUST выбросить NotFound.
4. WHEN создаётся или удаляется комментарий, репозиторий MUST в той же транзакции обновить `comments_count` треда атомарным UPDATE с `GREATEST(comments_count + delta, 0)`. Приращение MUST считать БД, а не Python: чтение-изменение-запись теряет параллельные комментарии в один тред.
5. `add_like` MUST использовать `INSERT ... ON CONFLICT DO NOTHING` по ключу (comment_id, user_id) - конкурентный повторный лайк не ошибка.
6. Треды удалённого клуба уносит каскад БД (FK `threads.club_id` ON DELETE CASCADE) в транзакции, удалившей клуб; комменты и лайки - каскады по thread_id/comment_id. Кода для этого случая нет: обработчик `handle_clubs_deleted` удалён вместе с событиями (#78).
7. `delete_user_content(user_id, delete_threads, delete_comments)` MUST делать только то, чего не знает БД - удаление по флагам запроса. WHEN `delete_threads=true`, метод MUST посчитать треды автора по клубам, удалить их и вернуть {club_id: удалено} для коррекции счётчиков клубов вызывающим; WHEN `false` - тредов не трогать, `author_id` зануляет FK ON DELETE SET NULL. Аналогично `delete_comments` для комментариев; при `delete_comments=true` счётчики затронутых тредов MUST уменьшаться до удаления строк, одним UPDATE с группировкой по `thread_id`.
8. Лайки пользователя MUST NOT удаляться кодом - `comment_likes.user_id` уносит FK ON DELETE CASCADE.
9. Батч-методы (`get_likes_counts`, `get_liked_comment_ids`) MUST возвращать пустой результат на пустой вход без запроса к БД.
10. Репозиторий MUST завершать записи `flush`, а не `commit` - транзакцию держит session dependency.
11. `get_threads` MUST принимать необязательный фильтр по этапу захода; при нём общее число MUST считаться отдельным `count_threads` с тем же набором условий - денормализованный счётчик клуба считает все треды и с фильтром неверен. Условия выборки и подсчёта MUST собираться в одном месте, чтобы они не могли разойтись.

## Constraints & Invariants
- Инвариант: лайк уникален на пару (comment_id, user_id) - констрейнт `uq_comment_likes_comment_id_user_id`.
- Инвариант: `author_id` и `user_id` - настоящие FK на users (SET NULL у авторства, CASCADE у лайков): целостность держит БД. За `delete_user_content` остаётся только то, чего FK не делают, - удаление по флагам запроса и данные для коррекции счётчиков.
- Инвариант: `reading_stage_id` - FK на reading_stages (SET NULL): репозиторий фильтрует по ней, но никогда не читает сам этап.
- Инвариант: `comments_count` равен числу комментариев треда. Счётчик своего домена: ведётся в одной транзакции с самим комментарием, событий для него нет. Комментарии, уходящие каскадом вместе с тредом, счётчика не касаются - строки треда уже нет.
- Инвариант: UPDATE счётчика MUST помечать загруженный объект треда просроченным (`synchronize_session="fetch"`) - иначе повторное чтение в той же сессии придёт из identity map со старым значением.

## Failure Behavior
1. IF `delete_thread`/`delete_comment`/`remove_like` не находит строку, THEN метод MUST завершиться без ошибки (идемпотентное удаление), счётчик комментариев MUST остаться прежним.

## Conformance
Реализация конформна, когда выполняет поведения 1-11, держит инварианты уникальности лайка, FK-ссылок и счётчика комментариев и правило отказа 1. Проверяется тестами tests/threads/, tests/comments/ и tests/bookclubs/test_denormalized_counters.py.