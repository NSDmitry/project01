---
title: "Bookclubs repository: доступ к book_clubs, club_members, book_club_genres"
status: accepted
tags:
  - "bookclubs"
  - "domain:bookclubs"
  - "spec"
---

## Purpose & Scope
Контракт слоя хранения bookclubs: `BookClubRepository` (@app/bookclubs/repository.py). Потребители - @app/bookclubs/service.py, порт `ClubsPort` домена threads (`get_book_club`, `is_member`) и обработчики событий. Вне scope: резолв жанров и владельцев (спек сервиса).

## Surface
- CRUD: `create_book_club`, `get_book_clubs`, `get_book_club`, `update_book_club`, `delete_book_club`.
- Участие: `is_member`, `get_members`, `join_book_club`, `remove_member`.
- Жанры: `set_genres`, `get_genre_ids`, `handle_genres_deleted`.
- События: `handle_user_deleted`, `change_threads_count`.
- Модели: `BookClub`, `ClubMember`, `BookClubGenre` - @app/bookclubs/models.py.

## Normative Behavior
1. WHEN создаётся клуб, репозиторий MUST в одной транзакции создать клуб, добавить владельца в участники и привязать жанры.
2. `get_book_clubs` MUST поддерживать фильтры: `relation=owner` (owner_id), `relation=member` (подзапрос по club_members), подстрочный ILIKE-поиск по имени/описанию/жанрам с экранированием `%`, `_`, `\`; сортировка по `BookClub.id`, результат `(items, total)`.
3. `delete_book_club`, `set_genres` и `update_book_club` MUST проверять владельца через `require_permission` до изменения.
4. `set_genres` MUST заменять набор жанров целиком (delete + insert).
5. `update_book_club` MUST применять только переданные поля (название, описание) и оставлять непереданные без изменений; жанры и состав участников MUST оставаться нетронутыми.
6. WHEN приходит USER_DELETED с `delete_clubs=true`, `handle_user_deleted` MUST удалить клубы владельца и вернуть их id (для CLUBS_DELETED); при `false` - занулить `owner_id`; членство пользователя MUST удаляться всегда.
7. `change_threads_count` MUST менять счётчик атомарным UPDATE с `GREATEST(threads_count + delta, 0)` - защита от ухода в минус при дублях событий (at-least-once доставка).
8. Репозиторий MUST завершать записи `flush`, а не `commit` - транзакцию держит session dependency.

## Constraints & Invariants
- Инвариант: участник уникален на пару (club_id, user_id) - составной PK club_members; повторный join ловится IntegrityError.
- Инвариант: имя клуба уникально (unique constraint на name).
- Инвариант: фильтр по `relation` осмыслен только вместе с пользователем - оба параметра опциональны по отдельности, но `relation` без пользователя недопустим.
- Инвариант: изменения атрибутов загруженной модели фиксируются `flush`, а не `refresh` - сессия создаётся с `autoflush=False`, поэтому `refresh` перечитал бы строку и молча затёр несохранённые правки.

## Failure Behavior
1. IF имя клуба занято, THEN `create_book_club` и `update_book_club` MUST откатить и выбросить Conflict.
2. IF повторный join, THEN `join_book_club` MUST откатить и выбросить Conflict.
3. IF leave без членства, THEN `remove_member` MUST выбросить Conflict.
4. IF клуб не найден, THEN `get_book_club` MUST выбросить NotFound.
5. IF задан `relation`, но не передан пользователь, THEN `get_book_clubs` MUST выбросить ошибку, а не игнорировать фильтр - молчаливый пропуск вернул бы вызывающему весь каталог клубов вместо его собственных.

## Conformance
Реализация конформна, когда выполняет поведения 1-8, держит инварианты уникальности и правила отказов 1-5. Проверяется тестами tests/bookclubs/.
