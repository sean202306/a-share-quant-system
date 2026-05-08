"""Database Initialization Script

Run this script to initialize the database schema.
Usage: python -m src.data.init_db
"""

from src.config import config
from src.data.db_schema import init_database
from src.logger import get_logger

logger = get_logger(__name__)


def main():
    """Initialize database"""
    logger.info(f"Initializing database at {config.DB_PATH}")
    try:
        init_database()
        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    main()
