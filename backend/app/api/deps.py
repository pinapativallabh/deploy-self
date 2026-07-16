"""
FastAPI dependency injection providers.

WHY THIS EXISTS:
FastAPI's Depends() system injects resources into endpoint functions.
Centralizing dependencies here means:
  - Endpoints declare WHAT they need, not HOW to get it
  - Resource lifecycle (create, yield, cleanup) is handled consistently
  - Testing becomes trivial — override dependencies with mocks

WHY GENERATOR DEPENDENCIES:
The generator pattern (yield inside a function) gives us setup/teardown
semantics. Code before yield runs before the endpoint; code after yield
runs after the response is sent. This ensures database sessions are
always closed, even if the endpoint raises an exception.
"""

from collections.abc import Generator

from redis.asyncio import Redis
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session for the duration of a single request.

    Creates a new SQLAlchemy session, yields it to the endpoint, and
    guarantees it is closed afterward. Each request gets its own session
    to avoid cross-request state contamination.

    Usage in endpoints:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis(request: Request) -> Redis:
    """
    Provide the shared Redis client from application state.

    Unlike get_db, this does NOT create a new client per request. The Redis
    client uses an internal connection pool, so sharing a single client
    across requests is safe and efficient.

    The client is created during app startup (lifespan) and stored on
    app.state. This dependency simply retrieves it.

    Usage in endpoints:
        @router.get("/example")
        async def example(redis: Redis = Depends(get_redis)):
            ...
    """
    return request.app.state.redis
