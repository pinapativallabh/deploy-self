import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger("app.main")

app = FastAPI(
    title=settings.APP_NAME,
    description="ForgeDeploy PaaS Control Plane API",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production phases
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Monitoring"])
async def health_check():
    logger.debug("Health check triggered")
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV
    }
