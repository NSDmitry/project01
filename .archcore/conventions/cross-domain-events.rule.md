---
title: "Кросс-доменное взаимодействие: прямые вызовы через deps.py"
status: accepted
tags:
  - "architecture"
  - "conventions"
---

## Rule
1. Кросс-доменный вызов - прямой: сервис типизируется конкретным классом соседнего домена (репозиторий или сервис), инстанс подставляет `deps.py` домена-потребителя. Портов-протоколов (`ports.py`) больше нет и заводить их MUST NOT.
2. Возвращаемые типы кросс-доменных методов - контракты из `app.core.contracts` (UserSummary, GenreResponse, BookResponse) или ORM-модель владельца данных; потребитель не лезет в чужие таблицы напрямую, SQL остаётся в репозитории домена-владельца.
3. Роутеры MAY импортировать `app.iam.deps` (identity-провайдер `get_current_user`/`get_optional_user`).
4. Событийной шины больше нет: `app/core/events.py` и RabbitMQ удалены (задача #79 эпика #75), событий в проекте нет и заводить их MUST NOT. Каскад удаления пользователя выполняется прямыми вызовами в транзакции запроса (#78), `threads_count` правится прямым вызовом `change_threads_count` в той же транзакции (#77).

## Rationale
Распил на микросервисы отменён (эпик #75): порты дублировали сигнатуры реальных репозиториев и оплачивали гибкость, которая не понадобится. Прямой вызов через deps.py проще, проходит mypy по реальным типам и не прячет зависимость за протоколом.

## Examples
### Good
```python
# service.py
from app.bookclubs.repository import BookClubRepository  # конкретный класс соседа

class ThreadService:
    book_club_repository: BookClubRepository  # инстанс подставляет deps.py
```
### Bad
```python
class ClubsPort(Protocol):  # порт-протокол - удалены в #76, не заводить заново
    async def get_book_club(self, club_id: int) -> Any: ...
```

## Enforcement
Manual review; grep `ports.py`, `Protocol` и `core.events` в `app/*/` должен быть пуст.