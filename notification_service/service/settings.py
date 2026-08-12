import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    # Статический секрет приёма батчей. Пустой = приём закрыт (любой запрос 401).
    internal_token: str = ""
    telegram_bot_token: str = ""

    model_config = SettingsConfigDict(
        env_file=".env.test" if os.getenv("IS_TEST") else ".env",
        extra="ignore",
    )


# Значения без дефолтов приходят из окружения/.env, а не из вызова.
settings = Settings()  # type: ignore[call-arg]
