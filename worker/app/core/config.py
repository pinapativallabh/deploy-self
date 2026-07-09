import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class WorkerSettings(BaseSettings):
    WORKER_NAME: str = "ForgeDeploy Worker"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "info"

    # Redis Settings (Declared but not yet wired into worker logic)
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Docker Settings (Declared but not yet wired into worker logic)
    DOCKER_HOST: str = "unix:///var/run/docker.sock"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = WorkerSettings()
