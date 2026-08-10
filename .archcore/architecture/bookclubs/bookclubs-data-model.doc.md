---
title: "Data model: bookclubs"
status: accepted
tags:
  - "architecture"
  - "data-model"
  - "domain:bookclubs"
---

SQLAlchemy schema · 8 entities.

| Entity | Key relations |
|--------|---------------|
| BookClub (book_clubs) | 1:N ClubMember; 1:N Reading; 1:N ClubInvite; 1:N ClubJoinRequest; N:M Genre via book_club_genres; owner_id -> users (логическая, nullable) |
| ClubMember (club_members) | N:1 BookClub (FK CASCADE); user_id -> users (логическая) |
| BookClubGenre (book_club_genres) | N:1 BookClub (FK CASCADE); genre_id -> genres (логическая) |
| ClubInvite (club_invites) | N:1 BookClub (FK CASCADE); created_by -> users (логическая) |
| ClubJoinRequest (club_join_requests) | N:1 BookClub (FK CASCADE); user_id -> users (логическая) |
| Reading (readings) | N:1 BookClub (FK CASCADE); N:1 Book (FK SET NULL, nullable); 1:N ReadingStage; 1:N ReadingProgress |
| ReadingStage (reading_stages) | N:1 Reading (FK CASCADE); обратная ссылка из тредов - логическая, по id |
| ReadingProgress (reading_progress) | N:1 Reading (FK CASCADE); N:1 ReadingStage (FK SET NULL, nullable); user_id -> users (логическая) |

Relations: связи на users и genres кросс-доменные, только по id, без FK. Связь readings на книгу - FK с SET NULL, как у тредов: удаление книги не должно уносить историю чтения клуба. Обратная связь тредов на этап захода (`threads.reading_stage_id`) сделана без FK: треды в чужом домене, а FK ещё и создавал бы пересечение блокировок с обработчиком CLUBS_DELETED, который чистит треды в своей сессии, пока удаление клуба ещё не зафиксировано.

Приватность и роли:

- `book_clubs.privacy` - как попасть в клуб: `public`, `by_request` или `by_invite`. Значения держит CHECK, а не enum-тип Postgres: добавить значение потом дешевле. На видимость клуба в каталоге и поиске режим не влияет.
- `club_members.role` - `member` или `moderator`. Роли владельца в этой колонке нет: владение хранит `book_clubs.owner_id`, и дублировать его ролью значило бы завести второй источник правды. Роль владельца в ответах выводится из `owner_id`.
- `club_invites.code` уникален глобально - по коду вступают, не зная id клуба. `expires_at` NULL - код бессрочный.
- `club_join_requests` - одна строка на пару (клуб, пользователь): повторная подача переписывает статус, а не плодит заявки.

Денормализованные счётчики book_clubs:

- `threads_count` - ведётся по событиям THREAD_CREATED/THREAD_DELETED, треды в чужом домене.
- `members_count` - ведётся репозиторием в одной транзакции с club_members. Событий нет: участники в своём домене, поэтому счётчик и строка членства меняются вместе и разъехаться могут только при правках в обход репозитория.

Генерируемые колонки book_clubs:

- `search_vector` (tsvector) - полнотекстовое представление названия и описания, вес A у названия и B у описания. Считается СУБД при записи, кодом не поддерживается.

## Индексы

| Индекс | Колонки | Обслуживает |
|--------|---------|-------------|
| ix_book_clubs_owner_id | owner_id | фильтр списка клубов по владению, обнуление владельца при удалении пользователя |
| ix_club_members_user_id | user_id | фильтр списка клубов по участию, удаление пользователя |
| ix_book_club_genres_genre_id | genre_id | фильтр клубов по жанру |
| ix_book_clubs_search_vector | search_vector (GIN) | полнотекстовый поиск клубов |
| uq_club_invites_code | code (unique) | вступление по коду приглашения |
| ix_club_invites_club_id | club_id | каскадное удаление приглашений вместе с клубом |
| uq_club_join_requests_club_id_user_id | club_id, user_id (unique) | одна заявка на пару; club_id как префикс - очередь заявок клуба |
| ix_club_join_requests_user_id | user_id | чистка заявок при удалении пользователя |
| ix_readings_club_id_id | club_id, id | архив заходов клуба со свежими сверху |
| uq_readings_active_club_id | club_id (unique, WHERE finished_at IS NULL) | единственность незакрытого захода у клуба |
| uq_reading_stages_reading_id_position | reading_id, position (unique) | этапы захода по порядку; reading_id как префикс |
| uq_reading_progress_reading_id_user_id | reading_id, user_id (unique) | одна отметка участника на заход; reading_id как префикс |
| ix_reading_progress_user_id | user_id | удаление пользователя, выход из клуба |
| ix_reading_progress_stage_id | stage_id | ON DELETE SET NULL при удалении этапа |

Инварианты:

- Составные первичные ключи club_members и book_club_genres ведут club_id первой
  колонкой, поэтому выборка участников и жанров клуба покрыта ими как префиксом.
  Выборка по одному user_id или genre_id этими ключами не покрывается и требует
  отдельного индекса.
- Владелец клуба ровно один и хранится ровно в одном месте - `book_clubs.owner_id`.
  Он же всегда числится в club_members, но его строка несёт роль `member`:
  расхождение между колонкой владения и ролью поэтому невозможно.
- Приглашения и заявки удалённого клуба уносит каскад БД по club_id - кода для
  этого нет. Заявки удалённого пользователя чистит код: FK на users нет.
- Счётчики тредов и участников читаются из денормализованных колонок, а не
  считаются агрегатом: стоимость агрегата растёт с размером клуба, а не страницы,
  и на каталоге умножалась на число клубов страницы.
- Текст поиска и его индекс не могут разъехаться: `search_vector` генерируемый,
  СУБД пересчитывает его в той же записи, что меняет название или описание. Это
  причина выбрать генерируемую колонку, а не триггер и не поддержку в коде.
- Незакрытый заход у клуба ровно один, и это держит частичный уникальный индекс,
  а не проверка в коде: два параллельных создания прошли бы предварительный SELECT
  оба и вставили бы две строки.
- Прогресс участника ссылается на этап, а не хранит его номер копией: сравнение
  «в графике» идёт по позиции этапа, а позиция живёт в одной строке этапа.
- Расширение pg_trgm в схеме остаётся после удаления триграммных индексов: оно
  могло быть установлено не только этими миграциями.
