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
1. WHEN создаётся клуб, репозиторий MUST в одной транзакции создать клуб, добавить владельца в участники, привязать жанры и завести счётчик участников равным единице.
2. `get_book_clubs` MUST поддерживать фильтры: `relation=owner` (owner_id), `relation=member` (подзапрос по club_members), подстрочный ILIKE-поиск по имени/описанию/жанрам с экранированием `%`, `_`, `\`; сортировка по `BookClub.id`, результат `(items, total)`.
3. Ветви подстрочного поиска (имя, описание, жанры) MUST объединяться через UNION, а не через OR в одном WHERE. Неиндексируемая ветвь внутри OR заставляет планировщик читать таблицу целиком и обесценивает триграммные индексы: с OR запрос идёт Seq Scan независимо от их наличия.
4. `delete_book_club`, `set_genres` и `update_book_club` MUST проверять владельца через `require_permission` до изменения.
5. `set_genres` MUST заменять набор жанров целиком (delete + insert).
6. `update_book_club` MUST применять только переданные поля (название, описание) и оставлять непереданные без изменений; жанры и состав участников MUST оставаться нетронутыми.
7. `get_members` MUST отдавать только страницу идентификаторов участников. Общее число участников репозиторий не считает - его держит `BookClub.members_count`.
8. WHEN меняется состав участников (создание клуба, join, leave, удаление пользователя), репозиторий MUST в той же транзакции обновить `members_count` атомарным UPDATE с `GREATEST(members_count + delta, 0)`. Приращение MUST считать БД, а не Python: чтение-изменение-запись теряет параллельные join/leave по одному клубу.
9. WHEN приходит USER_DELETED с `delete_clubs=true`, `handle_user_deleted` MUST удалить клубы владельца и вернуть их id (для CLUBS_DELETED); при `false` - занулить `owner_id`; членство пользователя MUST удаляться всегда, а счётчики затронутых клубов - уменьшаться до удаления строк членства.
10. `change_threads_count` MUST менять счётчик атомарным UPDATE с `GREATEST(threads_count + delta, 0)` - защита от ухода в минус при дублях событий (at-least-once доставка).
11. Репозиторий MUST завершать записи `flush`, а не `commit` - транзакцию держит session dependency.

## Constraints & Invariants
- Инвариант: участник уникален на пару (club_id, user_id) - составной PK club_members; повторный join ловится IntegrityError.
- Инвариант: имя клуба уникально (unique constraint на name).
- Инвариант: `members_count` равен числу строк club_members этого клуба. В отличие от `threads_count` счётчик ведётся не событиями, а в одной транзакции с самим членством, поэтому разъехаться может только при правках в обход репозитория.
- Инвариант: UPDATE счётчика MUST помечать уже загруженный объект клуба просроченным (`synchronize_session="fetch"`) - иначе следующий `get_book_club` в той же сессии отдаст его из identity map со старым значением.
- Инвариант: фильтр по `relation` осмыслен только вместе с пользователем - оба параметра опциональны по отдельности, но `relation` без пользователя недопустим.
- Инвариант: изменения атрибутов загруженной модели фиксируются `flush`, а не `refresh` - сессия создаётся с `autoflush=False`, поэтому `refresh` перечитал бы строку и молча затёр несохранённые правки.

## Failure Behavior
1. IF имя клуба занято, THEN `create_book_club` и `update_book_club` MUST откатить и выбросить Conflict.
2. IF повторный join, THEN `join_book_club` MUST откатить и выбросить Conflict, счётчик участников MUST остаться прежним.
3. IF leave без членства, THEN `remove_member` MUST выбросить Conflict.
4. IF клуб не найден, THEN `get_book_club` MUST выбросить NotFound.
5. IF задан `relation`, но не передан пользователь, THEN `get_book_clubs` MUST выбросить ошибку, а не игнорировать фильтр - молчаливый пропуск вернул бы вызывающему весь каталог клубов вместо его собственных.

## Conformance
Реализация конформна, когда выполняет поведения 1-11, держит инварианты уникальности и счётчика участников и правила отказов 1-5. Проверяется тестами tests/bookclubs/, включая tests/bookclubs/test_denormalized_counters.py.
