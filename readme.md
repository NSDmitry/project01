Технологии:
- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Docker
- Prometheus
- Grafana

Запуск проекта:
- поднять контейнер с базой данных (можно через docker-compose db up -d)
- нужно создать файл .env с переменной DATABASE_URL, которая ссылается на базу данных
- выполнить команду alembic upgrade head
- запустить через uvicorn app.main:app --reload --log-level debug

Запуск тестов:
- нужно создать файл .env.test с переменной DATABASE_URL, которая ссылается на тестовую базу данных (контейнер нужно поднять заранее)
- выполнить команду IS_TEST=true pytest -v -s

Миграция базы:
- alembic revision --autogenerate -m "description"
- alembic upgrade head

Полезное:
- формат перемнной в .env DATABASE_URL=postgresql://user:password@host/dbname - логин, пароль, хост и имя базы
- поля для .env - DATABASE_URL, ORIGIN_URLS