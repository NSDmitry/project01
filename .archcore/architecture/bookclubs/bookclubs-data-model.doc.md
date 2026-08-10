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

Relations: связи на users и genres кросс-доменные, только по id, без FK.

Денормализованные счётчики book_clubs:

- `threads_count` - ведётся по событиям THREAD_CREATED/THREAD_DELETED, треды в чужом домене.
- `members_count` - ведётся репозиторием в одной транзакции с club_members. Событий нет: участники в своём домене, поэтому счётчик и строка членства меняются вместе и разъехаться могут только при правках в обход репозитория.

## Индексы

| Индекс | Колонки | Обслуживает |
|--------|---------|-------------|
| ix_book_clubs_owner_id | owner_id | фильтр списка клубов по владению, обнуление владельца при удалении пользователя |
| ix_club_members_user_id | user_id | фильтр списка клубов по участию, удаление пользователя |
| ix_book_club_genres_genre_id | genre_id | ветвь поиска клубов по жанру |
| ix_book_clubs_name_trgm | name (GIN, gin_trgm_ops) | подстрочный ILIKE-поиск по названию |
| ix_book_clubs_description_trgm | description (GIN, gin_trgm_ops) | подстрочный ILIKE-поиск по описанию |

Инварианты:

- Составные первичные ключи club_members и book_club_genres ведут club_id первой
  колонкой, поэтому выборка участников и жанров клуба покрыта ими как префиксом.
  Выборка по одному user_id или genre_id этими ключами не покрывается и требует
  отдельного индекса.
- Счётчики тредов и участников читаются из денормализованных колонок, а не
  считаются агрегатом: стоимость агрегата растёт с размером клуба, а не страницы,
  и на каталоге умножалась на число клубов страницы.
- Триграммные индексы работают только вместе с UNION-формой поискового запроса.
  Пока три ветви поиска стоят в одном OR, неиндексируемая ветвь роняет весь
  запрос в Seq Scan и GIN не используется. Менять индексы и форму запроса порознь
  бессмысленно.
