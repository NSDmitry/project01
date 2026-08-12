# Тесты

Тесты запускаются с отдельной конфигурацией через `.env.test`.

## 1. Поднять тестовую базу

```bash
docker compose -f docker-compose.test.yml up -d
```

Тестовая база публикуется на `localhost:5433`.

## 2. Проверить `.env.test`

Файл `.env.test` уже есть в репозитории:

```env
DATABASE_URL=postgresql://test_admin:test_password@localhost:5433/test_database
ORIGIN_URLS=["http://localhost:3000"]
```

## 3. Запустить тесты

```bash
IS_TEST=true pytest -s -v
```

`IS_TEST=true` переключает приложение на чтение настроек из `.env.test`. Схему тестовой базы фикстура `setup_test_db` поднимает сама через `alembic upgrade head` (тот же путь, что и в проде), отдельно мигрировать тестовую базу не нужно.

Если зависимости установлены через `Pipenv`, отключите автозагрузку дев-`.env` - иначе `Pipenv` подставит `DATABASE_URL` из основного `.env` и тесты уйдут в дев-базу:

```bash
PIPENV_DONT_LOAD_ENV=1 IS_TEST=true pipenv run pytest -s -v
```

Тесты прогоняются в CI на каждый PR в `main` - см. `.github/workflows/tests.yml` (Python 3.11, та же тестовая база через `docker-compose.test.yml`).

## Тесты notification-service

У сервиса доставки уведомлений свой прогон - из каталога `notification_service/`, на том же тестовом Postgres (`5433`); отдельную базу `test_notifications` тесты создают сами:

```bash
cd notification_service
IS_TEST=true python -m pytest
```

В CI этот прогон пока не подключён - запускается вручную.
