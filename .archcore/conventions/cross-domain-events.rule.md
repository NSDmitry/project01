---
title: "Кросс-доменное взаимодействие: порты и события, не импорты"
status: accepted
tags:
  - "architecture"
  - "conventions"
---

## Rule
1. Домен (`app/iam`, `app/threads`, `app/bookclubs`, `app/books`, `app/genres`) MUST NOT импортировать модули другого домена. Кросс-доменное чтение MUST идти через порты домена-потребителя (`app/<domain>/ports.py`, типы из `app.core.contracts`), кросс-доменные изменения данных - через события `app.core.events`.
2. Санкционированное исключение: роутеры MAY импортировать `app.iam.deps` (identity-провайдер `get_current_user`/`get_optional_user`) - помечено комментарием в месте импорта.

## Rationale
Подготовка к распилу монолита (PR #48): у таблиц нет кросс-доменных FK, консистентность держат события (USER_DELETED, CLUBS_DELETED и другие). Прямой импорт чужого репозитория создаёт связь, которая при выносе домена в сервис превращается в сетевой вызов молча.

## Examples
### Good
```python
from app.threads.ports import ClubsPort   # порт, реализация подставляется в deps
await events.publish(events.THREAD_CREATED, {"club_id": model.club_id})
```
### Bad
```python
from app.bookclubs.repository import BookClubRepository  # прямой импорт чужого домена
```

## Enforcement
Manual review; grep кросс-доменных импортов по `app/*/`, допустим только `app.iam.deps` в роутерах.