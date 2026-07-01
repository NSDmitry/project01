# Book Club API

Backend-сервис для книжного клуба на `FastAPI`.

Проект решает четыре базовые задачи:
- регистрация и авторизация пользователей;
- работа с пользовательским профилем;
- создание и управление книжными клубами;
- создание и сопровождение обсуждений внутри клубов.

Сервис использует `PostgreSQL`, `SQLAlchemy`, `Alembic` и отдаёт метрики в `Prometheus`.

## Стек

- `Python 3.11`
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
- `POST /api/auth/telegram` - вход и регистрация через Telegram Mini App по подписанным данным `initData`
- `POST /api/auth/logout` - завершение текущей сессии по заголовку `X-Session-Id`

### Пользователи

- `GET /api/users/current` - текущий пользователь
- `GET /api/users/public?user_id=...` - публичный профиль пользователя
- `PUT /api/users` - обновление имени и номера телефона
- `PUT /api/users/password` - смена пароля с завершением всех активных сессий

### Книжные клубы

- `POST /api/bookclubs` - создать клуб
- `GET /api/bookclubs` - получить список клубов; параметр `relation=owner` - клубы, где пользователь владелец, `relation=member` - клубы, в которых он состоит
- `GET /api/bookclubs/{club_id}` - получить клуб по `id`
- `DELETE /api/bookclubs/{club_id}` - удалить клуб
- `POST /api/bookclubs/{club_id}/join` - вступить в клуб
- `DELETE /api/bookclubs/{club_id}/leave` - выйти из клуба

### Обсуждения

- `GET /api/discussions/{club_id}` - получить обсуждения клуба
- `POST /api/discussions` - создать обсуждение
- `PUT /api/discussions/{discussion_id}` - обновить обсуждение
- `DELETE /api/discussions/{discussion_id}` - удалить обсуждение

Примечание: для защищённых методов проект использует заголовок `X-Session-Id`, а не `Authorization: Bearer`.

## Аутентификация и пароль

Проект использует серверные сессии. После успешной регистрации или входа API возвращает `session_id`, который нужно передавать в заголовке:

```text
X-Session-Id: <session_id>
```

### Жизненный цикл сессии

Живость сессии определяется только полем `last_used` (скользящее окно неактивности):

- `last_used` проставляется в момент создания сессии и обновляется при сетевых запросах, но не чаще одного раза в `5` минут (троттлинг, чтобы read-запрос не превращался в запись на каждый вызов);
- если с последнего использования прошло больше `30` дней, сессия считается невалидной - защищённый запрос получает `401` (проверка ленивая, на каждом запросе). В теле ответа `errors` содержит стабильный токен `session_expired` (на него клиент и ориентируется, чтобы увести пользователя на повторный вход), а `message` несёт человекочитаемое описание;
- отдельного поля абсолютного срока жизни нет: активная сессия живёт, пока ею пользуются.

Физически протухшие строки выметает фоновая чистка `python -m app.tasks.cleanup_sessions` - удаляет сессии с `last_used` старше `30` дней. В `docker-compose.yml` она запускается сервисом `cleanup` ежедневно в `03:00`.

Текущая password policy:
- минимум `8` символов;
- максимум `128` символов;
- хотя бы одна заглавная буква;
- хотя бы одна строчная буква;
- хотя бы одна цифра;
- пароль не может быть пустым и не должен состоять только из пробелов.

Смена пароля через `PUT /api/users/password` инвалидирует все активные сессии пользователя. После этого нужно выполнить повторный вход.

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
DATABASE_URL=postgresql://admin:123123@localhost:5432/database
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

## Тесты

Тесты запускаются с отдельной конфигурацией через `.env.test`.

### 1. Поднять тестовую базу

```bash
docker compose -f docker-compose.test.yml up -d
```

Тестовая база публикуется на `localhost:5433`.

### 2. Проверить `.env.test`

Файл `.env.test` уже есть в репозитории:

```env
DATABASE_URL=postgresql://test_admin:test_password@localhost:5433/test_database
ORIGIN_URLS=["http://localhost:3000"]
```

### 3. Запустить тесты

```bash
IS_TEST=true pytest -s -v
```

`IS_TEST=true` переключает приложение на чтение настроек из `.env.test`. Схему тестовой базы фикстура `setup_test_db` поднимает сама через `alembic upgrade head` (тот же путь, что и в проде), отдельно мигрировать тестовую базу не нужно.

Если зависимости установлены через `Pipenv`, отключите автозагрузку дев-`.env` - иначе `Pipenv` подставит `DATABASE_URL` из основного `.env` и тесты уйдут в дев-базу:

```bash
PIPENV_DONT_LOAD_ENV=1 IS_TEST=true pipenv run pytest -s -v
```

Тесты прогоняются в CI на каждый PR в `main` - см. `.github/workflows/tests.yml` (Python 3.11, та же тестовая база через `docker-compose.test.yml`).

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
- Смена пароля завершает все активные сессии пользователя, включая текущую.
- Сессия протухает после `30` дней неактивности; протухший `X-Session-Id` даёт `401`, клиенту нужно войти заново.
- Публичный профиль пользователя не должен содержать приватные поля вроде `session_id`.
- Основной сценарий локальной работы: поднять БД, применить миграции, запустить `uvicorn`, затем отдельно гонять `pytest`.
