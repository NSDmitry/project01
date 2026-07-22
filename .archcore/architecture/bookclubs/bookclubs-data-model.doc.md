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