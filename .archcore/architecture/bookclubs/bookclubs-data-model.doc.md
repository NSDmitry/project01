---
title: "Data model: bookclubs"
status: accepted
tags:
  - "architecture"
  - "data-model"
  - "domain:bookclubs"
---

SQLAlchemy schema · 3 entities.

| Entity | Key relations |
|--------|---------------|
| BookClub (book_clubs) | 1:N ClubMember; N:M Genre via book_club_genres; owner_id -> users (логическая, nullable) |
| ClubMember (club_members) | N:1 BookClub (FK CASCADE); user_id -> users (логическая) |
| BookClubGenre (book_club_genres) | N:1 BookClub (FK CASCADE); genre_id -> genres (логическая) |

Relations: связи на users и genres кросс-доменные, только по id, без FK; book_clubs.threads_count - денормализованный счётчик, ведётся по событиям THREAD_CREATED/THREAD_DELETED.

## Индексы

| Индекс | Колонки | Обслуживает |
|--------|---------|-------------|
| ix_book_clubs_owner_id | owner_id | фильтр списка клубов по владению, обнуление владельца при удалении пользователя |
| ix_club_members_user_id | user_id | фильтр списка клубов по участию, удаление пользователя |

Инварианты:

- Составные первичные ключи club_members и book_club_genres ведут club_id первой
  колонкой, поэтому выборка участников и жанров клуба покрыта ими как префиксом.
  Выборка по одному user_id этими ключами не покрывается и требует отдельного
  индекса.
- Счётчик тредов клуба читается из денормализованной колонки, а не считается
  подзапросом по чужому домену: задача решена без индекса и без обратной
  зависимости.
- Поиск клуба по подстроке в названии и описании идёт полным сканом. Btree для
  поиска с произвольной позиции непригоден в принципе; при росте каталога это
  закрывается триграммным индексом, а не обычным.