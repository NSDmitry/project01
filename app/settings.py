import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env.test" if os.getenv("IS_TEST") else ".env"
    )


settings = Settings()