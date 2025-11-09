import logging
from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseModel):
    MAX_ATTEMPTS: int = 3
    RETRY_BASE_DELAY: int = 5


class Settings(BaseSettings):
    MODE: str = "DEV"

    LOG_LEVEL: int = logging.INFO

    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()


settings = get_settings()
worker_settings = get_worker_settings()
