# Структура проекта

```text
app/
  core/            инфраструктура: база данных, ошибки, общие модели и схемы
  iam/             домен идентичности: пользователи, сессии, аутентификация (в т.ч. Telegram)
  bookclubs/       домен книжных клубов: клубы и членство
  discussions/     домен обсуждений: треды и комментарии
migrations/        Alembic-миграции
tests/             интеграционные и API-тесты
```

Каждый домен устроен одинаково: `router.py` (HTTP-роуты), `service.py` (бизнес-логика), `repository.py` (работа с базой), `models.py` (SQLAlchemy-модели), `schemas.py` (Pydantic-схемы), `deps.py` (FastAPI-зависимости). Направление зависимостей: `discussions -> bookclubs -> iam -> core`, обратных импортов быть не должно (исключение - `bookclubs/models.py` импортирует `Thread` для счётчика `threads_count`).

## Наблюдаемость

Приложение экспортирует метрики на:

```text
/metrics
```

Метрики собираются через `prometheus-fastapi-instrumentator`.
