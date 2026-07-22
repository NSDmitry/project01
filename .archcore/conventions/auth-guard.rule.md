---
title: "Авторизация хендлеров через get_current_user"
status: draft
tags:
  - "auth"
  - "conventions"
---

## Rule
1. Каждый HTTP-хендлер, требующий авторизации, MUST получать пользователя через `Depends(get_current_user)` из `app.iam.deps` (опционально - `get_optional_user`). Применяется к `app/*/router.py`.
2. Хендлер MUST NOT читать заголовок `X-Session-Id` или проверять сессию самостоятельно.

## Rationale
Единственная точка проверки сессии (35 использований в 5 роутерах) - истечение, лимиты и формат ошибки меняются в одном месте; самодельная проверка обойдёт эти правила молча.

## Examples
### Good
```python
async def delete_thread(thread_id: PathId, user: Principal = Depends(get_current_user)):
    ...
```
### Bad
```python
async def delete_thread(thread_id: PathId, request: Request):
    sid = request.headers.get("X-Session-Id")  # самодельная проверка сессии
```

## Enforcement
Manual review; тесты авторизации в tests/sso_tests/ падают при обходе dependency.