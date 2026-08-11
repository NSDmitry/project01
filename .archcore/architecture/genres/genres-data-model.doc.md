---
title: "Data model: genres"
status: accepted
tags:
  - "architecture"
  - "data-model"
  - "domain:genres"
---

SQLAlchemy schema · 1 entity.

| Entity | Key relations |
|--------|---------------|
| Genre (genres) | внутридоменных связей нет; на genres ссылается book_club_genres.genre_id (FK, ON DELETE CASCADE - удаление жанра отвязывает его от клубов силами БД) |