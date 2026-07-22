---
title: "Threads repository: доступ к threads, comments, comment_likes"
status: draft
tags:
  - "domain:threads"
  - "spec"
  - "threads"
---

## Purpose & Scope
Контракт слоя хранения threads: `ThreadRepository`, `CommentRepository` (@app/threads/repository.py). Потребители - @app/threads/service.py и обработчики событий CLUBS_DELETED / USER_DELETED. Вне scope: проверки прав и членства (спек сервиса).

## Surface
- `ThreadRepository`: `get_threads`, `get_thread`, `create_thread`, `update_thread`, `delete_thread`, `handle_clubs_deleted`, `handle_user_deleted`.
- `CommentRepository`: `get_comments`, `get_comment`, `create_comment`, `update_comment`, `delete_comment`, `add_like`, `remove_like`, `get_likers`, `get_likes_counts`, `get_liked_comment_ids`.
- Модели: `Thread`, `Comment`, `CommentLike` - @app/threads/models.py.

## Normative Behavior
1. `get_threads` MUST сортировать по `created_at DESC, id DESC`; `get_comments` - по `created_at ASC, id ASC`; `get_likers` - по `created_at DESC, id DESC`; все MUST возвращать `(items, total)`.
2. WHEN `get_thread`/`get_comment` не находит строку, репозиторий MUST выбросить NotFound.
3. `add_like` MUST использовать `INSERT ... ON CONFLICT DO NOTHING` по ключу (comment_id, user_id) - конкурентный повторный лайк не ошибка.
4. WHEN приходит CLUBS_DELETED, `handle_clubs_deleted` MUST явно удалить треды перечисленных клубов (FK threads.club_id на book_clubs нет); комменты и лайки удаляют каскады БД.
5. WHEN приходит USER_DELETED с `delete_threads=false`, `handle_user_deleted` MUST занулить `author_id` тредов автора; при `true` - удалить их и вернуть {club_id: удалено} для коррекции счётчиков клубов; аналогично `delete_comments` для комментариев.
6. `handle_user_deleted` MUST всегда удалять лайки пользователя (CommentLike.user_id).
7. Батч-методы (`get_likes_counts`, `get_liked_comment_ids`) MUST возвращать пустой результат на пустой вход без запроса к БД.
8. Репозиторий MUST завершать записи `flush`, а не `commit` - транзакцию держит session dependency.

## Constraints & Invariants
- Инвариант: лайк уникален на пару (comment_id, user_id) - констрейнт `uq_comment_likes_comment_id_user_id`.
- Инвариант: `author_id` и `user_id` - логические ссылки на iam без FK; целостность держат обработчики событий, не БД.

## Failure Behavior
1. IF `delete_thread`/`delete_comment`/`remove_like` не находит строку, THEN метод MUST завершиться без ошибки (идемпотентное удаление).
2. IF `handle_clubs_deleted` получает пустой список, THEN метод MUST выйти без запроса к БД.

## Conformance
Реализация конформна, когда выполняет поведения 1-8, держит инварианты уникальности лайка и логических ссылок и правила отказов 1-2. Проверяется тестами tests/threads/ и tests/comments/.