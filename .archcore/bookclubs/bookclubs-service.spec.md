---
title: "Bookclubs service: клубы, участие, жанры, поиск"
status: accepted
tags:
  - "bookclubs"
  - "domain:bookclubs"
  - "spec"
---

## Purpose & Scope
Контракт бизнес-логики bookclubs: `BookClubService` (@app/bookclubs/service.py). Потребители - @app/bookclubs/router.py и обработчики событий. Вне scope: HTTP-коды (спек роутера), SQL (спек репозитория).

## Surface
- `BookClubService`: `create_book_club`, `get_book_clubs`, `search_book_clubs`, `get_book_club`, `get_members`, `update_book_club`, `delete_book_club`, `join`, `leave`, `set_genres`.
- Кросс-доменные зависимости - только порты `GenresPort`, `UsersPort` (@app/bookclubs/ports.py) и события @app/core/events.py.

## Normative Behavior
1. WHEN создаётся клуб или заменяются жанры, сервис MUST проверить каждый код жанра через `GenresPort.get_by_codes`; дубли кодов MUST схлопываться до уникальных.
2. WHEN клуб удалён, сервис MUST опубликовать CLUBS_DELETED с `club_ids` - треды удалённого клуба чистит домен threads (FK нет).
3. WHEN собирается ответ, сервис MUST подтягивать владельца через `UsersPort.get_summaries_by_ids` и жанры через `GenresPort.get_by_ids` батчем на всю страницу (не N+1); owner и genres в модели не живут, клуб хранит только id.
4. Жанры клуба в ответе MUST идти в порядке `sort_order` каталога жанров.
5. WHEN вызывается `search_book_clubs` с непустым `query`, сервис MUST получить id подходящих жанров у `GenresPort.search_ids` и передать их в репозиторий.
6. WHEN обновляются название и описание клуба, сервис MUST отдавать ту же модель ответа, что и остальные операции над клубом - с владельцем, жанрами и счётчиками.
7. `members_count` в ответе и `total` страницы участников MUST браться из столбца загруженного клуба. Сервис MUST NOT считать участников агрегатом: стоимость такого счёта росла с размером клуба, а не страницы, и на каталоге умножалась на число клубов страницы.

## Constraints & Invariants
- Инвариант: сервис не импортирует модули iam/genres/threads напрямую - только порты и события.
- Инвариант: `threads_count` клуба - денормализованный столбец, изменяется только обработчиками событий THREAD_CREATED/THREAD_DELETED, не пользовательскими операциями.
- Инвариант: `members_count` - тоже денормализованный столбец, но своего домена: его ведёт репозиторий в одной транзакции с club_members, событий для него нет.
- Инвариант: название и описание клуба редактируются только владельцем и только через `update_book_club`; жанры - отдельной операцией `set_genres`.

## Failure Behavior
1. IF среди кодов жанров есть неизвестный, THEN сервис MUST выбросить UnprocessableEntity с перечнем неизвестных кодов.
2. IF клуб не найден, THEN сервис MUST пробросить NotFound репозитория.
3. IF `owner_id` клуба NULL (владелец удалил аккаунт без удаления клубов), THEN ответ MUST содержать `owner = null`; такой клуб через API удалить и отредактировать нельзя - принятое ограничение, проверка владельца не проходит ни для кого.

## Conformance
Реализация конформна, когда выполняет поведения 1-7, держит инварианты портов и обоих счётчиков и правила отказов 1-3. Проверяется тестами tests/bookclubs/.
