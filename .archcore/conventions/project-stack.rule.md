---
title: "Project stack"
status: accepted
tags:
  - "conventions"
  - "stack"
---

Код на Python 3.11.
Веб-фреймворк - FastAPI; альтернативные фреймворки не вводить без ADR.
Хранение - SQLAlchemy, база - PostgreSQL; схема БД меняется только через Alembic-миграции.
Тесты - pytest (основной раннер).