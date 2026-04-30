from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def parse_cors(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://release:release@postgres:5432/release_board"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8
    cors_origins: Annotated[list[str], NoDecode, BeforeValidator(parse_cors)] = ["http://localhost:5173"]
    admin_username: str = "admin"
    admin_password: str = "admin123"
    token_encryption_key: str | None = None
    scheduler_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
