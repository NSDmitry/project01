Запуск проекта локально:
1. pipenv shell
2. uvicorn main:app --reload

Для миграции:
1. alembic revision --autogenerate -m "Write description here"
2. alembic upgrade head


Собрать и задеплоить образ из директории:
1. docker build --platform=linux/amd64 -t project01 .
2. docker tag project01 nsdmitrij/project01:latest
3. docker push nsdmitrij/project01:latest

Скачать образ и запустить на сервере:
1. docker pull nsdmitrij/project01:latest
2. docker run -d -p 8000:8000 --name project01 nsdmitrij/project01:latest

Если не запускается:
1. docker stop project01
2. docker rm project01