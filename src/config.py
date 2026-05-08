"""Configuration Management

Supports Dev (macOS) and Prod (Ubuntu) environments.
All sensitive information is loaded from .env file.
"""

import os
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)


class Config:
    """Base configuration class"""

    # Environment
    ENV: Literal["dev", "prod"] = os.getenv("ENV", "dev")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Paths (cross-platform using pathlib)
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / os.getenv("DATA_PATH", "data")
    LOGS_DIR = PROJECT_ROOT / os.getenv("LOG_PATH", "logs")
    DB_PATH = DATA_DIR / os.getenv("DB_PATH", "quant_system.db")

    # Tushare API
    TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")
    TUSHARE_BASE_URL = "http://api.tushare.pro"

    # API Configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
    RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    RATE_LIMIT_DELAY = 0.5  # seconds between requests

    # LLM Configuration (for Phase 4)
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-xxx")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen2")
    LLM_MAX_TOKENS = 2048

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Data Pipeline
    SYNC_BATCH_SIZE = 500  # batch size for database inserts
    SYNC_QUOTE_DAYS = 5  # default days to sync daily quotes
    SYNC_FUND_FLOW_DAYS = 10  # default days to sync fund flow

    def __init__(self):
        """Initialize configuration and create necessary directories"""
        self._ensure_directories()
        self._validate_config()

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def _validate_config(self) -> None:
        """Validate critical configuration"""
        if not self.TUSHARE_TOKEN:
            raise ValueError(
                "TUSHARE_TOKEN is not set. "
                "Please set it in .env file or environment variable."
            )

    @property
    def is_dev(self) -> bool:
        """Check if running in dev environment"""
        return self.ENV == "dev"

    @property
    def is_prod(self) -> bool:
        """Check if running in prod environment"""
        return self.ENV == "prod"

    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        return {
            "ENV": self.ENV,
            "DEBUG": self.DEBUG,
            "DB_PATH": str(self.DB_PATH),
            "DATA_DIR": str(self.DATA_DIR),
            "LOGS_DIR": str(self.LOGS_DIR),
            "TUSHARE_BASE_URL": self.TUSHARE_BASE_URL,
            "MAX_RETRIES": self.MAX_RETRIES,
            "RETRY_BACKOFF_FACTOR": self.RETRY_BACKOFF_FACTOR,
            "REQUEST_TIMEOUT": self.REQUEST_TIMEOUT,
            "LOG_LEVEL": self.LOG_LEVEL,
        }


# Global configuration instance
config = Config()
