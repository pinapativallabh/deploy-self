"""
FastAPI application entry point.

This module creates the application instance, wires up lifecycle events,
exception handlers, middleware, and routers. It is the single place where
all infrastructure components are assembled.

WHY LIFESPAN INSTEAD OF on_event:
FastAPI deprecated @app.on_event("startup") and @app.on_event("shutdown")
in favor of the lifespan context manager. Lifespan provides a clean
setup/teardown pattern where resources created during startup are
guaranteed to be cleaned up during shutdown — even if startup fails
partway through.
"""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import close_redis, create_redis_client, verify_redis
from app.core.exceptions import register_exception_handlers
from app.api.health import router as health_router

setup_logging()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application startup and shutdown.

    Startup:
      - Create and verify Redis client
      - Log readiness

    Shutdown:
      - Close Redis connections gracefully

    The database engine does NOT need explicit startup/shutdown here.
    SQLAlchemy's engine uses a lazy connection pool — connections are
    created on first use and cleaned up when the process exits.
    """
    logger.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.APP_ENV)

    # --- Redis ---
    redis_client = create_redis_client(settings.redis_url)
    app.state.redis = redis_client
    await verify_redis(redis_client)

    logger.info("%s is ready", settings.APP_NAME)

    yield

    # --- Shutdown ---
    logger.info("Shutting down %s...", settings.APP_NAME)
    await close_redis(app.state.redis)
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    description="Self-hosted application control plane",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# --- Exception Handlers ---
register_exception_handlers(app)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production via configuration
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health_router)
