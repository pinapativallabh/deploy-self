"""
Redis client lifecycle management.

WHY THIS EXISTS:
Redis serves as the backbone for future background job queues, caching, and
pub/sub. This module provides functions to create, verify, and close Redis
connections. It does NOT implement any Redis-based features — only the
connection infrastructure.

WHY FUNCTIONS INSTEAD OF A CLASS:
A RedisManager class would add a layer of indirection for three simple
operations (create, verify, close). Functions are simpler and compose
cleanly with FastAPI's lifespan pattern. The actual Redis client instance
lives on app.state, managed by the FastAPI lifespan — not as module-level
global state.

WHY ASYNC REDIS:
FastAPI is an async framework. Using sync Redis operations inside async
endpoints blocks the event loop. redis-py provides redis.asyncio with the
same API surface, so there's no additional complexity cost.
"""

import logging

from redis.asyncio import Redis

logger = logging.getLogger("app.redis")


def create_redis_client(url: str) -> Redis:
    """
    Create a Redis client from a connection URL.

    The client uses a connection pool internally. Connections are established
    lazily — creating the client does not immediately connect to Redis.
    """
    return Redis.from_url(url, decode_responses=True)


async def verify_redis(client: Redis) -> bool:
    """
    Verify Redis connectivity by sending a PING command.

    Returns True if Redis responds, False otherwise. Never raises — the
    application should start even if Redis is temporarily unreachable.
    """
    try:
        await client.ping()
        logger.info("Redis connection verified")
        return True
    except Exception as exc:
        logger.warning("Redis is unreachable: %s", exc)
        return False


async def close_redis(client: Redis) -> None:
    """
    Close the Redis connection pool gracefully.

    Called during application shutdown to release connections cleanly.
    """
    await client.aclose()
    logger.info("Redis connection closed")
