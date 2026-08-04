import asyncio
import logging
import uuid
from arq.connections import RedisSettings

from app.core.config import settings
from app.services.deployment_service import DeploymentService
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger("app.worker")

async def startup(ctx):
    logger.info("ARQ Worker starting up...")

async def shutdown(ctx):
    logger.info("ARQ Worker shutting down...")

async def execute_deployment(ctx, deployment_id: uuid.UUID | str):
    """
    ARQ job for executing deployments.
    Runs the blocking execute_deployment in a thread pool.
    """
    if isinstance(deployment_id, str):
        deployment_id = uuid.UUID(deployment_id)
        
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, DeploymentService.execute_deployment, deployment_id)

class WorkerSettings:
    functions = [execute_deployment]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
    )
    max_jobs = settings.MAX_CONCURRENT_DEPLOYMENTS
    job_timeout = settings.MAX_DEPLOYMENT_DURATION_MINUTES * 60
