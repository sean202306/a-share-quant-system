"""Logging Configuration

Provides centralized logging setup for the application.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from src.config import config


class Logger:
    """Centralized logger configuration"""

    _loggers: dict[str, logging.Logger] = {}

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get or create a logger instance

        Args:
            name: Logger name (usually __name__)

        Returns:
            Configured logger instance
        """
        if name in Logger._loggers:
            return Logger._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(config.LOG_LEVEL)

        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(config.LOG_FORMAT)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (for prod)
        if config.is_prod:
            log_file = config.LOGS_DIR / f"{name}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10485760, backupCount=5  # 10MB per file
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        Logger._loggers[name] = logger
        return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Convenience function to get a logger

    Args:
        name: Logger name (defaults to __name__ of caller)

    Returns:
        Configured logger instance
    """
    if name is None:
        name = "a-share-quant"
    return Logger.get_logger(name)
