"""
Centralized logging configuration.

WHY THIS EXISTS:
Every module needs logging. Without centralized configuration, each module
would configure its own logger inconsistently. This module ensures:
  - Consistent format across all log output
  - Single place to change log level
  - Stdout output (correct for containerized applications)

WHY STDLIB LOGGING INSTEAD OF STRUCTLOG/LOGURU:
Python's built-in logging module is sufficient. structlog adds structured
JSON output which is valuable at scale, but adds a dependency and learning
curve. We can migrate to structlog later if JSON logging becomes necessary
for log aggregation. For now, the format string provides enough structure.

WHY STDOUT INSTEAD OF FILES:
Containers should log to stdout. Docker and orchestrators capture stdout
and route it to their own log aggregation. Writing to files inside a
container creates state that disappears when the container restarts.
"""

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure the root logger for the application.

    Called once during application startup. Uses force=True to override
    any logging configuration that libraries may have set during import.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger("app")
    logger.info("Logging initialized at level: %s", settings.LOG_LEVEL.upper())
