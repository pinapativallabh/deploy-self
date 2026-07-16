"""
SQLAlchemy database engine and session configuration.

WHY THIS EXISTS:
This module creates the two things every SQLAlchemy application needs:
  1. An Engine — manages the connection pool to PostgreSQL
  2. A sessionmaker — factory that produces Session objects for each request

WHY SYNC INSTEAD OF ASYNC SQLALCHEMY:
SQLAlchemy 2.x supports async via asyncio + asyncpg. We use sync because:
  - psycopg2 is the most battle-tested PostgreSQL driver
  - Sync sessions are simpler to understand and debug
  - FastAPI runs sync dependencies in a threadpool automatically
  - Async can be adopted later if profiling shows the threadpool is a bottleneck

WHY NOT CREATE THE ENGINE AT MODULE IMPORT TIME:
The engine is created at module level because it's stateless until a connection
is actually requested. SQLAlchemy engines use lazy connection pools — importing
this module does NOT open a database connection. The first actual query triggers
pool initialization. This means importing the module is always safe, even if
PostgreSQL is temporarily unreachable.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
"""
pool_pre_ping=True:  Before handing out a connection from the pool, SQLAlchemy
                     sends a lightweight ping. If the connection is stale (e.g.,
                     PostgreSQL restarted), it's discarded and a fresh one is
                     created. This prevents "connection already closed" errors.

pool_size=5:         Keep 5 persistent connections in the pool. This is the
                     SQLAlchemy default and appropriate for a single-instance
                     backend. Increase if connection wait times appear in logs.

max_overflow=10:     Allow up to 10 additional connections beyond pool_size
                     during traffic spikes. These overflow connections are
                     closed when returned to the pool rather than kept alive.
"""

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)
"""
autocommit=False:  We want explicit transactions. Every session starts a
                   transaction that must be committed or rolled back.

autoflush=False:   Don't automatically flush pending changes before queries.
                   Explicit flushing prevents surprise SQL statements and
                   makes debugging easier.
"""


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    WHY DECLARATIVEBASE INSTEAD OF declarative_base():
    SQLAlchemy 2.x introduced DeclarativeBase as a modern replacement for the
    legacy declarative_base() function. It provides better type checker support
    and integrates with Mapped[] type annotations. All future models will
    inherit from this class.
    """

    pass
