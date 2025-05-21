import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    origin_urls: List[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env.test" if os.getenv("IS_TEST") else ".env"
    )


settings = Settings()