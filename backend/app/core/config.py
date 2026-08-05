"""
Centralized application configuration.

WHY THIS EXISTS:
Every application needs configuration. Environment variables are the standard
mechanism (12-factor app), but accessing os.environ directly throughout the
codebase creates three problems:
  1. No validation — a typo in a variable name silently returns None
  2. No type safety — everything is a string
  3. No single source of truth — config is scattered across modules

WHY PYDANTIC SETTINGS:
Pydantic Settings validates ALL configuration at import time. If a required
variable is missing or has the wrong type, the application fails immediately
with a clear error — not minutes later when someone first queries the database.

WHY NOT A YAML/TOML CONFIG FILE:
Environment variables are the deployment standard. Every orchestrator (Docker
Compose, Kubernetes, systemd) supports them natively. Config files require
volume mounting and parsing logic for no additional benefit at this scale.
"""

import secrets

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Values are loaded in this priority order (highest to lowest):
      1. Environment variables set in the shell/container
      2. Values from the .env file
      3. Default values defined here

    Every field that has a default value is optional in the .env file.
    Fields without defaults will cause a startup error if missing.
    """

    # --- Application ---
    APP_NAME: str = "Bonk"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    LOG_LEVEL: str = "info"

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Public-facing host used to generate deployment URLs.
    # Set this to the server's public IP or domain in production
    # (e.g. "ec2-1-2-3-4.compute.amazonaws.com" or "deploy.example.com").
    PUBLIC_HOST: str = "localhost"

    # --- PostgreSQL ---
    POSTGRES_USER: str = "bonk"
    POSTGRES_PASSWORD: str = "bonk_dev_password"
    POSTGRES_DB: str = "bonk"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433

    # --- Application Settings ---
    ALLOW_REGISTRATION: bool = True
    MAX_USERS: int = 5
    HEALTH_CHECK_TIMEOUT: int = 30
    POLLING_INTERVAL: int = 1
    BUILD_TIMEOUT: int = 600
    REPO_CACHE_PATH: str = "repos"
    CLEANUP_RETENTION: int = 5
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Safety & Limits ---
    MAX_REQUEST_BODY_MB: int = 5
    RATE_LIMIT_LOGIN_MAX: int = 10
    RATE_LIMIT_LOGIN_WINDOW: int = 60
    RATE_LIMIT_REGISTER_MAX: int = 5
    RATE_LIMIT_REGISTER_WINDOW: int = 60
    GIT_CLONE_TIMEOUT: int = 300
    WEBHOOK_TIMEOUT: int = 10
    MAX_DEPLOYMENT_DURATION_MINUTES: int = 15
    MAX_CONCURRENT_DEPLOYMENTS: int = 2
    MAX_DEPLOYMENT_LOG_MB: int = 10
    CONTAINER_CPU_LIMIT: float = 1.0
    CONTAINER_MEMORY_LIMIT: str = "512m"
    MAX_PROJECT_NAME_LENGTH: int = 64
    MAX_REPO_URL_LENGTH: int = 256
    MAX_ENV_VARS_PER_PROJECT: int = 50
    MAX_ENV_VAR_SIZE: int = 4096

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # --- JWT / Authentication ---
    JWT_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-" + secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Reject insecure development defaults outside local development."""
        if self.APP_ENV != "development" and self.JWT_SECRET_KEY.startswith(
            "CHANGE-ME-IN-PRODUCTION-"
        ):
            raise ValueError("JWT_SECRET_KEY must be explicitly set outside development")
        if self.MAX_USERS < 1:
            raise ValueError("MAX_USERS must be greater than 0")
        if self.MAX_REQUEST_BODY_MB < 1:
            raise ValueError("MAX_REQUEST_BODY_MB must be greater than 0")
        if self.RATE_LIMIT_LOGIN_MAX < 1 or self.RATE_LIMIT_REGISTER_MAX < 1:
            raise ValueError("Rate limits must be greater than 0")
        if self.MAX_DEPLOYMENT_DURATION_MINUTES < 1:
            raise ValueError("MAX_DEPLOYMENT_DURATION_MINUTES must be greater than 0")
        if self.MAX_CONCURRENT_DEPLOYMENTS < 1:
            raise ValueError("MAX_CONCURRENT_DEPLOYMENTS must be greater than 0")
        if self.MAX_DEPLOYMENT_LOG_MB < 1:
            raise ValueError("MAX_DEPLOYMENT_LOG_MB must be greater than 0")
        if self.CONTAINER_CPU_LIMIT <= 0:
            raise ValueError("CONTAINER_CPU_LIMIT must be positive")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Build the SQLAlchemy connection string from individual components."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Build the Redis connection string from individual components."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
