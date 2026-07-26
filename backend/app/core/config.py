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

from pydantic import computed_field
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

    # --- PostgreSQL ---
    POSTGRES_USER: str = "bonk"
    POSTGRES_PASSWORD: str = "bonk_dev_password"
    POSTGRES_DB: str = "bonk"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433

    # --- Application Settings ---
    HEALTH_CHECK_TIMEOUT: int = 30
    POLLING_INTERVAL: int = 1
    BUILD_TIMEOUT: int = 600
    REPO_CACHE_PATH: str = "repos"
    CLEANUP_RETENTION: int = 5
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # --- JWT / Authentication ---
    # WHY NO DEFAULT FOR JWT_SECRET_KEY IN PRODUCTION:
    # The default value is only suitable for development. In production,
    # JWT_SECRET_KEY MUST be set via environment variable. Using a default
    # secret in production would mean every deployment shares the same
    # signing key — an attacker who reads the source code can forge tokens.
    #
    # We provide a default here to avoid breaking the development experience.
    # The application logs a warning at startup if the default is in use.
    JWT_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-" + secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """
        Build the SQLAlchemy connection string from individual components.

        WHY COMPUTED INSTEAD OF A SEPARATE ENV VAR:
        A single DATABASE_URL env var is convenient but forces the operator to
        construct URLs manually. Individual components are easier to override
        in Docker Compose and less error-prone. We assemble the URL internally.
        """
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
