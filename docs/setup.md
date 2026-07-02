# Запуск проекта

## Быстрый старт

### 1. Установить зависимости

Требуется `Python 3.11`.

Вариант с `pip` (так же ставит зависимости Docker и CI):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Либо через `Pipenv`:

```bash
pipenv --python 3.11 install --dev
pipenv shell
```

### 2. Поднять PostgreSQL

Локальная база поднимается через `docker-compose.yml`:

```bash
docker compose up -d db
```

По умолчанию контейнер публикует PostgreSQL на `localhost:5432`.

### 3. Создать `.env`

Пример минимального `.env`:

```env
DATABASE_URL=postgresql://admin:REDACTED@localhost:5432/database
ORIGIN_URLS=["http://localhost:3000","http://localhost:5173"]
```

Что означает:
- `DATABASE_URL` - строка подключения к основной базе данных
- `ORIGIN_URLS` - список origin'ов для CORS

### 4. Применить миграции

Схема базы управляется только `Alembic` - приложение не создаёт таблицы при старте, поэтому миграции нужно применить вручную:

```bash
alembic upgrade head
```

Подробнее - в [Миграции](migrations.md).

### 5. Запустить приложение

```bash
uvicorn app.main:app --reload --log-level debug
```

После запуска сервис будет доступен на [http://localhost:8000](http://localhost:8000).

## Запуск через Docker Compose

Если нужен запуск приложения и базы вместе:

```bash
docker compose up --build
```

Сервис приложения поднимается на `localhost:8000`, база данных на `localhost:5432`. Вместе с ними поднимается сервис `cleanup` - он раз в сутки в `03:00` чистит протухшие сессии.
