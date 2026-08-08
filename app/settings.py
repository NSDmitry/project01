import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    origin_urls: List[str] = Field(default_factory=list)
    telegram_bot_token: str = ""
    # Пустой ключ = запросы к Google Books без ключа (меньшие квоты).
    google_books_api_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    # Пусто = кросс-доменные события доставляются синхронно в том же процессе
    # (тесты, локальный запуск без брокера). Иначе - RabbitMQ.
    rabbitmq_url: str = ""
    # Пустой токен = эндпоинт /metrics отключён (404). Непустой = требуется Bearer-токен.
    metrics_token: str = ""
    # В проде выключить (DOCS_ENABLED=false), чтобы скрыть Swagger/ReDoc/OpenAPI.
    docs_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env.test" if os.getenv("IS_TEST") else ".env",
        # POSTGRES_* и прочие переменные в .env нужны docker-compose, не приложению.
        extra="ignore",
    )


# Значения без дефолтов приходят из окружения/.env, а не из вызова.
settings = Settings()  # type: ignore[call-arg]