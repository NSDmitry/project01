# Миграции

Схема базы управляется только `Alembic` - приложение не создаёт таблицы при старте.

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
