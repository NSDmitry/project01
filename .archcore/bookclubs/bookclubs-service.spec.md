---
title: "Bookclubs service: клубы, участие, жанры, поиск"
status: draft
tags:
  - "bookclubs"
  - "domain:bookclubs"
  - "spec"
---

## Purpose & Scope
Контракт бизнес-логики bookclubs: `BookClubService` (@app/bookclubs/service.py). Потребители - @app/bookclubs/router.py и обработчики событий. Вне scope: HTTP-коды (спек роутера), SQL (спек репозитория).

## Surface
- `BookClubService`: `create_book_club`, `get_book_clubs`, `search_book_clubs`, `get_book_club`, `get_members`, `delete_book_club`, `join`, `leave`, `set_genres`.
- Кросс-доменные зависимости - только порты `GenresPort`, `UsersPort` (@app/bookclubs/ports.py) и события @app/core/events.py.

## Normative Behavior
1. WHEN создаётся клуб или заменяются жанры, сервис MUST проверить каждый код жанра через `GenresPort.get_by_codes`; дубли кодов MUST схлопываться до уникальных.
2. WHEN клуб удалён, сервис MUST опубликовать CLUBS_DELETED с `club_ids` - треды удалённого клуба чистит домен threads (FK нет).
3. WHEN собирается ответ, сервис MUST подтягивать владельца через `UsersPort.get_summaries_by_ids` и жанры через `GenresPort.get_by_ids` батчем на всю страницу (не N+1); owner и genres в модели не живут, клуб хранит только id.
4. Жанры клуба в ответе MUST идти в порядке `sort_order` каталога жанров.
5. WHEN вызывается `search_book_clubs` с непустым `query`, сервис MUST получить id подходящих жанров у `GenresPort.search_ids` и передать их в репозиторий.

## Constraints & Invariants
- Инвариант: сервис не импортирует модули iam/genres/threads напрямую - только порты и события.
- Инвариант: `threads_count` клуба - денормализованный столбец, изменяется только обработчиками событий THREAD_CREATED/THREAD_DELETED, не пользовательскими операциями.

## Failure Behavior
1. IF среди кодов жанров есть неизвестный, THEN сервис MUST выбросить UnprocessableEntity с перечнем неизвестных кодов.
2. IF клуб не найден, THEN сервис MUST пробросить NotFound репозитория.
3. IF `owner_id` клуба NULL (владелец удалил аккаунт без удаления клубов), THEN ответ MUST содержать `owner = null`; такой клуб через API удалить нельзя - принятое ограничение, проверка владельца не проходит ни для кого.

## Conformance
Реализация конформна, когда выполняет поведения 1-5, держит инварианты портов и `threads_count` и правила отказов 1-3. Проверяется тестами tests/bookclubs/.