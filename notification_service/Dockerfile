# Отдельный образ notification-service: монолит в него не попадает.
FROM python:3.11

WORKDIR /app

# Копируем весь сервис и ставим его зависимости из pyproject.
COPY . .
RUN pip install --no-cache-dir .

# Запускаем не под root - меньше ущерба при компрометации процесса
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

# Приём батчей. Воркер и миграции запускаются тем же образом с другим command
# (см. docker-compose), не в старте приложения.
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000"]
