# Book Club API

Backend-сервис для книжного клуба на `FastAPI`.

Проект решает четыре базовые задачи:
- регистрация и авторизация пользователей;
- работа с пользовательским профилем;
- создание и управление книжными клубами;
- создание и сопровождение тредов внутри клубов.

## Стек

`Python 3.11`, `FastAPI`, `SQLAlchemy`, `PostgreSQL`, `Alembic`, `Docker Compose`, `Prometheus`.

## Быстрый старт

```bash
docker compose up --build
```

Сервис поднимется на [http://localhost:8000](http://localhost:8000). Локальный запуск без Docker - в [docs/setup.md](docs/setup.md).

## Документация

- [Запуск проекта](docs/setup.md) - установка зависимостей, `.env`, локальный запуск и Docker Compose
- [API](docs/api.md) - обзор всех ручек: аутентификация, пользователи, клубы, треды, комментарии
- [Аутентификация и сессии](docs/auth.md) - серверные сессии, жизненный цикл, password policy
- [Тесты](docs/testing.md) - тестовая база, `.env.test`, запуск, CI
- [Миграции](docs/migrations.md) - Alembic-only управление схемой
- [Структура проекта](docs/architecture.md) - домены, направление зависимостей, наблюдаемость
