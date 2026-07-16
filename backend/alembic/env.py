"""
Alembic migration environment.

This is the script that Alembic runs when executing migrations. It handles
two modes:

  1. Offline mode — generates SQL scripts without a live database connection.
     Useful for reviewing migrations before applying them, or for environments
     where direct database access is restricted.

  2. Online mode — connects to the database and applies migrations directly.
     This is the standard mode for development and deployment.

WHY THE DATABASE URL COMES FROM config.py:
Alembic's default template puts sqlalchemy.url in alembic.ini. This means
database credentials would live in a non-.env file that's easy to accidentally
commit. Instead, we import our Settings class and use the same database_url
that the application uses. Single source of truth.

WHY target_metadata USES Base.metadata:
Alembic's --autogenerate feature compares the database schema against the
ORM model metadata to detect differences. By pointing target_metadata at
our Base.metadata, Alembic will automatically detect when we add, modify,
or remove model classes. Without this, autogenerate produces empty migrations.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.session import Base

# Alembic Config object — provides access to values in alembic.ini
config = context.config

# Set the SQLAlchemy URL from our application settings.
# This overrides any sqlalchemy.url value in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Configure Python logging from the alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that Alembic uses for autogenerate.
# Import all models BEFORE this line so their tables are registered on Base.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL statements to stdout instead of executing them.
    Useful for review or for environments without direct DB access.

    Usage: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates an engine, connects to the database, and applies migrations
    within a transaction.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
