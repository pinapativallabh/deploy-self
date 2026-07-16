"""
Health check endpoint.

WHY THIS EXISTS:
Health endpoints serve two audiences:
  1. Orchestrators (Docker, Kubernetes) — determine if the container should
     receive traffic or be restarted
  2. Operators — quickly verify that the backend and its dependencies are
     functioning after a deployment

WHY INDIVIDUAL DEPENDENCY CHECKS:
Reporting "healthy" or "unhealthy" as a single boolean is insufficient.
When something breaks, the operator needs to know WHICH dependency failed.
Checking each dependency individually and reporting per-component status
eliminates guesswork.

WHY 200 WHEN HEALTHY AND 503 WHEN DEGRADED:
200 tells the load balancer "this instance can serve requests."
503 tells it "route traffic elsewhere." The body still contains per-component
detail so operators can diagnose the issue from the response alone.
"""

import logging

from fastapi import APIRouter
from sqlalchemy import text
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.db.session import SessionLocal

router = APIRouter(tags=["Monitoring"])
logger = logging.getLogger("app.health")


def _check_postgres() -> dict:
    """Verify PostgreSQL connectivity by executing a trivial query."""
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"status": "healthy"}
        finally:
            db.close()
    except Exception as exc:
        logger.warning("PostgreSQL health check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


async def _check_redis(request: Request) -> dict:
    """Verify Redis connectivity by sending a PING command."""
    try:
        redis = request.app.state.redis
        await redis.ping()
        return {"status": "healthy"}
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


@router.get("/health")
async def health_check(request: Request) -> JSONResponse:
    """
    Report application health including dependency status.

    Returns:
        200 — all dependencies are healthy
        503 — one or more dependencies are unreachable
    """
    postgres_status = _check_postgres()
    redis_status = await _check_redis(request)

    all_healthy = (
        postgres_status["status"] == "healthy"
        and redis_status["status"] == "healthy"
    )

    payload = {
        "status": "healthy" if all_healthy else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "dependencies": {
            "postgres": postgres_status,
            "redis": redis_status,
        },
    }

    status_code = 200 if all_healthy else 503
    return JSONResponse(content=payload, status_code=status_code)
