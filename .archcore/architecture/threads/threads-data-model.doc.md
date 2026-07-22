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