# Book Club API

Backend-сервис для книжного клуба на `FastAPI`.

Проект решает четыре базовые задачи:
- регистрация и авторизация пользователей;
- работа с пользовательским профилем;
- создание и управление книжными клубами;
- создание и сопровождение обсуждений внутри клубов.

Сервис использует `PostgreSQL`, `SQLAlchemy`, `Alembic` и отдаёт метрики в `Prometheus`.

## Стек

- `Python 3.9`
- `FastAPI`
- `SQLAlchemy`
- `PostgreSQL`
- `Alembic`
- `Docker Compose`
- `Prometheus`

## Что есть в API

### Аутентификация

- `POST /api/auth/register` - регистрация по имени, номеру телефона и паролю
- `POST /api/auth/login` - вход по номеру телефона и паролю
- `POST /api/auth/logout` - завершение текущей сессии по заголовку `X-Session-Id`
- `POST /api/auth/telegram/login` - вход через `telegram_id`, с автоматической регистрацией при необходимости

### Пользователи

- `GET /api/users/current` - текущий пользователь
- `GET /api/users/public?user_id=...` - публичный профиль пользователя
- `PUT /api/users` - обновление имени и номера телефона

### Книжные клубы

- `POST /api/bookclubs` - создать клуб
- `GET /api/bookclubs` - получить список клубов
- `GET /api/bookclubs/owned` - клубы, которыми владеет текущий пользователь
- `GET /api/bookclubs/{club_id}` - получить клуб по `id`
- `DELETE /api/bookclubs/{club_id}` - удалить клуб
- `POST /api/bookclubs/{club_id}/join` - вступить в клуб
- `DELETE /api/bookclubs/{club_id}/leave` - выйти из клуба

### Обсуждения

- `GET /api/disscussions/{club_id}` - получить обсуждения клуба
- `POST /api/disscussions` - создать обсуждение
- `PUT /api/disscussions/{discussion_id}` - обновить обсуждение
- `DELETE /api/disscussions/{discussion_id}` - удалить обсуждение

Примечание: для защищённых методов проект использует заголовок `X-Session-Id`, а не `Authorization: Bearer`.

## Быстрый старт

### 1. Поднять PostgreSQL

Локальная база поднимается через `docker-compose.yml`:

```bash
docker compose up -d db
```

По умолчанию контейнер публикует PostgreSQL на `localhost:5432`.

### 2. Создать `.env`

Пример минимального `.env`:

```env
DATABASE_URL=postgresql://admin:123123@localhost:5432/database
ORIGIN_URLS=["http://localhost:3000","http://localhost:5173"]
```

Что означает:
- `DATABASE_URL` - строка подключения к основной базе данных
- `ORIGIN_URLS` - список origin'ов для CORS

### 3. Применить миграции

```bash
alembic upgrade head
```

### 4. Запустить приложение

```bash
uvicorn app.main:app --reload --log-level debug
```

После запуска сервис будет доступен на [http://localhost:8000](http://localhost:8000).

## Запуск через Docker Compose

Если нужен запуск приложения и базы вместе:

```bash
docker compose up --build
```

Сервис приложения поднимается на `localhost:8000`, база данных на `localhost:5432`.

## Тесты

Тесты запускаются с отдельной конфигурацией через `.env.test`.

### 1. Поднять тестовую базу

```bash
docker compose -f docker-compose.test.yml up -d
```

Тестовая база публикуется на `localhost:5433`.

### 2. Создать `.env.test`

```env
DATABASE_URL=postgresql://test_admin:test_password@localhost:5433/test_database
ORIGIN_URLS=["http://localhost:3000"]
```

### 3. Запустить тесты

```bash
IS_TEST=true pytest -s -v
```

`IS_TEST=true` переключает приложение на чтение настроек из `.env.test`.

## Миграции

Создать миграцию:

```bash
alembic revision --autogenerate -m "description"
```

Применить миграции:

```bash
alembic upgrade head
```

Если локальная схема сильно разъехалась и нужно быстро пересобрать её с нуля:

```bash
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
alembic upgrade head
```

Это разрушительная операция. Использовать только для локальной разработки.

## Наблюдаемость

Приложение экспортирует метрики на:

```text
/metrics
```

Метрики собираются через `prometheus-fastapi-instrumentator`.

## Структура проекта

```text
app/
  api/
    routers/       HTTP-роуты
    services/      бизнес-логика
  core/            зависимости, ошибки, общие модели
  db/
    models/        SQLAlchemy-модели
    repositories/  работа с базой
  schemas/         Pydantic-схемы
migrations/        Alembic-миграции
tests/             интеграционные и API-тесты
```

## Практические замечания

- Сессия пользователя хранится через `session_id`, который нужно передавать в заголовке `X-Session-Id`.
- `logout` идемпотентен: повторный вызов не должен ломать клиентский сценарий.
- Публичный профиль пользователя не должен содержать приватные поля вроде `session_id`.
- Основной сценарий локальной работы: поднять БД, применить миграции, запустить `uvicorn`, затем отдельно гонять `pytest`.
