"""SQLite Database Schema Definition

Defines all tables for the quantitative analysis system.
"""

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


# SQL schema definitions
CREATE_STOCKS_TABLE = """
CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    area TEXT,
    industry TEXT,
    market TEXT,
    list_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_DAILY_QUOTES_TABLE = """
CREATE TABLE IF NOT EXISTS daily_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    vol REAL,
    amount REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_date),
    FOREIGN KEY(ts_code) REFERENCES stocks(ts_code)
)
"""

CREATE_FUND_FLOW_TABLE = """
CREATE TABLE IF NOT EXISTS fund_flow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    buy_sm_volume REAL,
    buy_sm_amount REAL,
    sell_sm_volume REAL,
    sell_sm_amount REAL,
    net_sm_volume REAL,
    net_sm_amount REAL,
    buy_md_volume REAL,
    buy_md_amount REAL,
    sell_md_volume REAL,
    sell_md_amount REAL,
    net_md_volume REAL,
    net_md_amount REAL,
    buy_lg_volume REAL,
    buy_lg_amount REAL,
    sell_lg_volume REAL,
    sell_lg_amount REAL,
    net_lg_volume REAL,
    net_lg_amount REAL,
    net_inflow REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_date),
    FOREIGN KEY(ts_code) REFERENCES stocks(ts_code)
)
"""

CREATE_INDICATORS_TABLE = """
CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    ema20 REAL,
    ema60 REAL,
    macd REAL,
    macd_signal REAL,
    macd_hist REAL,
    rsi14 REAL,
    atr14 REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_date),
    FOREIGN KEY(ts_code) REFERENCES stocks(ts_code)
)
"""

CREATE_CONCEPT_SECTORS_TABLE = """
CREATE TABLE IF NOT EXISTS concept_sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id TEXT NOT NULL,
    concept_name TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(concept_id, ts_code),
    FOREIGN KEY(ts_code) REFERENCES stocks(ts_code)
)
"""

CREATE_SECTOR_DAILY_PERFORMANCE_TABLE = """
CREATE TABLE IF NOT EXISTS sector_daily_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id TEXT NOT NULL,
    concept_name TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    close_change REAL,
    close_change_pct REAL,
    vol REAL,
    amount REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(concept_id, trade_date)
)
"""

CREATE_SYNC_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    last_sync_date TEXT,
    status TEXT DEFAULT 'pending',
    total_records INTEGER,
    inserted_records INTEGER,
    updated_records INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(table_name)
)
"""

# Index creation for performance
CREATE_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_daily_quotes_ts_code ON daily_quotes(ts_code)",
    "CREATE INDEX IF NOT EXISTS idx_daily_quotes_date ON daily_quotes(trade_date)",
    "CREATE INDEX IF NOT EXISTS idx_fund_flow_ts_code ON fund_flow(ts_code)",
    "CREATE INDEX IF NOT EXISTS idx_fund_flow_date ON fund_flow(trade_date)",
    "CREATE INDEX IF NOT EXISTS idx_indicators_ts_code ON indicators(ts_code)",
    "CREATE INDEX IF NOT EXISTS idx_indicators_date ON indicators(trade_date)",
    "CREATE INDEX IF NOT EXISTS idx_sector_perf_date ON sector_daily_performance(trade_date)",
]

ALL_TABLES = [
    CREATE_STOCKS_TABLE,
    CREATE_DAILY_QUOTES_TABLE,
    CREATE_FUND_FLOW_TABLE,
    CREATE_INDICATORS_TABLE,
    CREATE_CONCEPT_SECTORS_TABLE,
    CREATE_SECTOR_DAILY_PERFORMANCE_TABLE,
    CREATE_SYNC_LOG_TABLE,
]


def init_database() -> None:
    """Initialize all database tables and indices"""
    import sqlite3

    try:
        conn = sqlite3.connect(str(config.DB_PATH))
        cursor = conn.cursor()

        # Create all tables
        for table_sql in ALL_TABLES:
            cursor.execute(table_sql)
            logger.debug(f"Created/verified table from: {table_sql[:50]}...")

        # Create indices
        for index_sql in CREATE_INDICES:
            cursor.execute(index_sql)
            logger.debug(f"Created/verified index: {index_sql[:50]}...")

        conn.commit()
        logger.info(f"Database initialized successfully: {config.DB_PATH}")

    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        conn.close()
