Запуск проекта локально:
1. pipenv shell
2. uvicorn main:app --reload

Для миграции:
alembic revision --autogenerate -m ""
alembic upgrade head


Собрать и задеплоить образ из директории:
docker build --platform=linux/amd64 -t project01 .
docker tag project01 nsdmitrij/project01:latest
docker push nsdmitrij/project01:latest

Скачать последние контейнеры и запустить на сервере:
docker-compose pull
docker-compose up -d

Если не запускается:
docker-compose down
docker rm project01