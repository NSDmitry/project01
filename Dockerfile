# Используем базовый образ Python 3.9.6
FROM python:3.9.6

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Открываем порт для сервера
EXPOSE 8000

# Запускаем FastAPI-приложение с Uvicorn
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000