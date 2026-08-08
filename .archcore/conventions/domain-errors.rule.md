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
3. Метод репозитория, который ищет строку, MUST возвращать `None`, если строка не найдена. Исключение - поиск по идентификатору, который вызывающий уже считает существующим (id из URL или из другой строки БД): такой метод MUST выбрасывать NotFound.
4. IF хотя бы для одного вызывающего отсутствие строки - штатный сценарий, THEN метод репозитория MUST возвращать `None`, а трактовку отсутствия MUST выбирать сервис.
5. Сервис MUST NOT пробрасывать `None` наружу, если трактовка отсутствия единственная и одинакова для всех вызывающих, - он MUST превратить её в доменную ошибку сам.

## Rationale
Глобальный хендлер APIException (@app/main.py) превращает иерархию в единый конверт `ResponseModel` с `errors`; HTTPException минует конверт и ломает формат ответа для клиентов. Сейчас иерархию импортируют 16 файлов, HTTPException в доменном коде не используется.

Правила 3-5 фиксируют границу, по которой уже разошлись репозитории (5 методов бросают NotFound, 6 возвращают `None`), и держат её от расползания в любую из двух крайностей:

- "везде `None`" стоит 19 повторов guard'а `if x is None: raise NotFound` на текущих вызовах поиска по id в сервисах и `deps`; забытый guard даёт AttributeError на `None` вместо 404;
- "везде исключение" ломает шесть штатных сценариев, где отсутствие - не ошибка: подстановка из Google Books, проверка занятости номера, `is_registered=False`, upsert Telegram-пользователя, guard гонки при вставке и анти-enumeration в `login`. Последний особенно важен: `login` намеренно не различает "номера нет" и "пароль неверный", и если репозиторий начнёт бросать NotFound, эта защита будет держаться на том, что вызывающий не забыл поставить `except`.

Обратная проверка правила 3: вокруг бросающих методов в сервисах нет ни одного `except NotFound`. Единственный catch в проекте (@app/iam/deps.py) не про "нашёл/не нашёл", а про подмену 404 на 401 для сессии без живого пользователя, у `user_sessions.user_id` нет FK.

## Examples
### Good
```python
from app.core.errors.errors import NotFound
raise NotFound(errors=["Тред с таким id не найден"])
```
```python
# репозиторий: поиск по вторичному признаку, трактовку выбирает сервис
async def get_user_by_phone_number(self, phone_number: str) -> User | None:
    ...
    return result.scalar_one_or_none()
```
### Bad
```python
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="not found")  # мимо конверта ResponseModel
```
```python
# репозиторий заранее выбрал 404, а вызывающему нужен был штатный путь
user = await repo.get_user_by_phone_number(phone)  # бросает NotFound
```
```python
try:
    user = await repo.get_user_by_phone_number(phone)
except NotFound:
    return LoginAvailableResponse(is_registered=False)  # исключение как поток управления
```

## Enforcement
Manual review; grep `HTTPException` по `app/` (ожидаемо только в main.py). Для правил 3-5: при добавлении метода поиска в репозиторий проверить всех вызывающих - если хоть одному отсутствие не ошибка, метод возвращает `None`.