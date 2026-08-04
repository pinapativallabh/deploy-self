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

WHY OAuth2PasswordBearer:
FastAPI's OAuth2PasswordBearer is not about OAuth2 per se — it's a standard
way to declare "this endpoint expects a Bearer token in the Authorization
header." It integrates with OpenAPI/Swagger so the docs show a lock icon
and an Authorize button. The tokenUrl points to our login endpoint, but
tokens are obtained via our JSON-based /auth/login, not the OAuth2 form.
"""

from collections.abc import Generator

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.orm import Session
from starlette.requests import Request
from arq.connections import ArqRedis

from app.db.session import SessionLocal

# Declare the token URL for OpenAPI documentation.
# This makes Swagger UI show the lock icon and Authorize button on
# protected endpoints. The actual login flow uses our /auth/login endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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


def get_arq_pool(request: Request) -> ArqRedis:
    """Provide the ARQ redis pool from application state."""
    return request.app.state.arq_pool


def get_raw_token(token: str = Depends(oauth2_scheme)) -> str:
    """
    Extract the raw JWT string from the Authorization header.

    This is used by the logout endpoint which needs the raw token string
    (not the decoded payload) to add it to the revocation list.
    """
    return token


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Authenticate the current request and return the User.

    This is the primary authentication dependency. Any endpoint that
    declares `current_user: User = Depends(get_current_user)` will:
      1. Require a valid Bearer token in the Authorization header
      2. Verify the token hasn't expired or been revoked
      3. Load and return the associated User from the database

    If any step fails, a 401 response is returned automatically.

    WHY IMPORT INSIDE THE FUNCTION:
    auth_service imports from models and schemas, which may import from
    db.session. Importing auth_service at module level in deps.py could
    create circular imports. The lazy import avoids this cleanly.
    """
    from app.services.auth_service import AuthError, validate_access_token

    try:
        return await validate_access_token(db, redis, token)
    except AuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


import time
from collections import defaultdict

_rate_limits = defaultdict(list)

class RateLimiter:
    """
    Rate limiting dependency using in-memory token bucket/list.
    Suitable for single-node deployments.
    """
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"{path}:{client_ip}"
        
        now = time.time()
        # Clean up old entries
        _rate_limits[key] = [t for t in _rate_limits[key] if now - t < self.window_seconds]
        
        if len(_rate_limits[key]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Too Many Requests")
            
        _rate_limits[key].append(now)
