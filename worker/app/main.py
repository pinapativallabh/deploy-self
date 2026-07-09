import time
import logging
from app.core.config import settings
from app.core.logging import setup_logging

def main():
    setup_logging()
    logger = logging.getLogger("worker.main")
    
    logger.info("Initializing %s", settings.WORKER_NAME)
    logger.info("Environment: %s", settings.APP_ENV)
    logger.info("Worker is ready and waiting for jobs...")
    
    try:
        while True:
            # Idle sleep loop to keep the process running.
            # In future phases, this will contain the Redis queue connection and job processing.
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Worker shutting down gracefully...")
    except Exception as e:
        logger.error("Worker encountered an error: %s", str(e), exc_info=True)

if __name__ == "__main__":
    main()
