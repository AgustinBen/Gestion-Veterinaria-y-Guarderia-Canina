from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./huellitas.db"
    secret_key: str = "change-me"
    session_minutes: int = 60
    password_min_length: int = 8
    guarderia_calendario_max_dias: int = Field(default=366, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
