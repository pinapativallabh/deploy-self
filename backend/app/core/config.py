import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "ForgeDeploy Backend"
    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    # Database Settings (Declared but not wired into backend logic yet)
    POSTGRES_USER: str = "forgeadmin"
    POSTGRES_PASSWORD: str = "forgepassword"
    POSTGRES_DB: str = "forgedeploy"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    # Redis Settings (Declared but not wired into backend logic yet)
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
