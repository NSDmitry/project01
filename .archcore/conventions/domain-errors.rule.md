---
title: "Ошибки только через иерархию app/core/errors"
status: accepted
tags:
  - "conventions"
  - "errors"
---

## Rule
1. Код приложения MUST сигнализировать об ошибках исключениями из `app/core/errors` (NotFound, Conflict, Unauthorized, Forbidden, BadRequest, UnprocessableEntity, TooManyRequests, ServiceUnavailable, InternalServerError). Применяется к `app/**/*.py`.
2. Код приложения MUST NOT выбрасывать `fastapi.HTTPException`; допустимое исключение - глобальные хендлеры в @app/main.py.

## Rationale
Глобальный хендлер APIException (@app/main.py) превращает иерархию в единый конверт `ResponseModel` с `errors`; HTTPException минует конверт и ломает формат ответа для клиентов. Сейчас иерархию импортируют 16 файлов, HTTPException в доменном коде не используется.

## Examples
### Good
```python
from app.core.errors.errors import NotFound
raise NotFound(errors=["Тред с таким id не найден"])
```
### Bad
```python
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="not found")  # мимо конверта ResponseModel
```

## Enforcement
Manual review; grep `HTTPException` по `app/` (ожидаемо только в main.py).