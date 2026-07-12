import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    origin_urls: List[str] = Field(default_factory=list)
    telegram_bot_token: str = ""
    redis_url: str = "redis://localhost:6379/0"
    # Пустой токен = эндпоинт /metrics отключён (404). Непустой = требуется Bearer-токен.
    metrics_token: str = ""
    # В проде выключить (DOCS_ENABLED=false), чтобы скрыть Swagger/ReDoc/OpenAPI.
    docs_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env.test" if os.getenv("IS_TEST") else ".env"
    )


settings = Settings()