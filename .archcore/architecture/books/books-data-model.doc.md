---
title: "Data model: books"
status: accepted
tags:
  - "architecture"
  - "data-model"
  - "domain:books"
---

SQLAlchemy schema · 1 entity.

| Entity | Key relations |
|--------|---------------|
| Book (books) | внутридоменных связей нет; на books ссылается threads.book_id (FK SET NULL) |