---
title: "Data model: threads"
status: accepted
tags:
  - "architecture"
  - "data-model"
  - "domain:threads"
---

SQLAlchemy schema · 3 entities.

| Entity | Key relations |
|--------|---------------|
| Thread (threads) | N:1 Book via book_id (FK SET NULL); 1:N Comment |
| Comment (comments) | N:1 Thread (FK CASCADE); 1:N CommentLike |
| CommentLike (comment_likes) | N:1 Comment (FK CASCADE); user_id -> users (логическая); UNIQUE (comment_id, user_id) |

Relations: лайк уникален на пару (comment_id, user_id); ссылка на пользователя кросс-доменная, без FK.

## Индексы

| Индекс | Колонки | Обслуживает |
|--------|---------|-------------|
| ix_threads_club_id_created_at_id | club_id, created_at, id | лента тредов клуба: фильтр и сортировка без отдельного Sort |
| ix_threads_author_id | author_id | удаление или анонимизация автора |
| ix_threads_book_id | book_id | ON DELETE SET NULL при удалении книги |
| ix_comments_thread_id_created_at_id | thread_id, created_at, id | комментарии треда: фильтр и сортировка без отдельного Sort |
| ix_comments_author_id | author_id | удаление или анонимизация автора |
| ix_comment_likes_user_id | user_id | удаление лайков при удалении пользователя |

Инварианты:

- Колонки в составных индексах перечислены по возрастанию. Btree читается в обе
  стороны, поэтому сортировка по убыванию обслуживается тем же индексом, и
  отдельный вариант с обратным порядком заводить не нужно.
- Ведущая колонка составного индекса выбрана так, чтобы он же покрывал выборку
  дочерних строк при каскадном удалении родителя.
- Уникальный ключ лайка (comment_id, user_id) обслуживает выборку по comment_id
  как префикс; выборка по одному user_id им не покрывается и требует отдельного
  индекса.