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