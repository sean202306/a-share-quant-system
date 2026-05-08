"""Data Pipeline Engine

Orchestrates incremental data synchronization from Tushare.
Supports UPSERT operations to avoid duplicates.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from src.config import config
from src.logger import get_logger
from src.data.db_schema import init_database
from src.data.tushare_client import TushareClient

logger = get_logger(__name__)


class DataPipeline:
    """Main data pipeline for incremental synchronization"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize data pipeline

        Args:
            db_path: Database path (defaults to config.DB_PATH)
        """
        self.db_path = db_path or config.DB_PATH
        self.client = TushareClient()
        self.conn: Optional[sqlite3.Connection] = None
        logger.info(f"DataPipeline initialized with db: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def __enter__(self):
        """Context manager entry"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.conn:
            self.conn.close()

    def sync_stocks(self) -> Dict[str, Any]:
        """Sync stock list

        Returns:
            Sync result dictionary
        """
        logger.info("Starting stocks sync...")
        result = {
            "table": "stocks",
            "status": "pending",
            "total": 0,
            "inserted": 0,
            "updated": 0,
            "error": None,
        }

        try:
            stocks = self.client.get_stocks()
            result["total"] = len(stocks)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                for stock in stocks:
                    cursor.execute(
                        """
                        INSERT INTO stocks (ts_code, symbol, name, area, industry, market, list_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(ts_code) DO UPDATE SET
                            name=excluded.name,
                            area=excluded.area,
                            industry=excluded.industry,
                            market=excluded.market,
                            list_date=excluded.list_date,
                            updated_at=CURRENT_TIMESTAMP
                        """,
                        (
                            stock.get("ts_code"),
                            stock.get("symbol"),
                            stock.get("name"),
                            stock.get("area"),
                            stock.get("industry"),
                            stock.get("market"),
                            stock.get("list_date"),
                        ),
                    )

                conn.commit()
                result["status"] = "success"
                result["inserted"] = len(stocks)

                logger.info(f"Stocks sync completed: {len(stocks)} stocks")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Stocks sync failed: {e}")

        return result

    def sync_daily_quotes(
        self, days: Optional[int] = None, ts_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync daily quotes (OHLCV data) - incremental

        Args:
            days: Number of days to sync (defaults to config.SYNC_QUOTE_DAYS)
            ts_code: Specific stock to sync (defaults to all)

        Returns:
            Sync result dictionary
        """
        days = days or config.SYNC_QUOTE_DAYS
        logger.info(f"Starting daily quotes sync (days={days})...")

        result = {
            "table": "daily_quotes",
            "status": "pending",
            "total": 0,
            "inserted": 0,
            "updated": 0,
            "error": None,
        }

        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get all stocks or specific stock
                if ts_code:
                    cursor.execute(
                        "SELECT ts_code FROM stocks WHERE ts_code = ?", (ts_code,)
                    )
                else:
                    cursor.execute("SELECT ts_code FROM stocks")

                stocks = [row[0] for row in cursor.fetchall()]
                total_records = 0

                for stock_code in stocks:
                    try:
                        quotes = self.client.get_daily_quotes(
                            stock_code, start_date, end_date
                        )

                        for quote in quotes:
                            cursor.execute(
                                """
                                INSERT INTO daily_quotes 
                                (ts_code, trade_date, open, high, low, close, vol, amount)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(ts_code, trade_date) DO UPDATE SET
                                    open=excluded.open,
                                    high=excluded.high,
                                    low=excluded.low,
                                    close=excluded.close,
                                    vol=excluded.vol,
                                    amount=excluded.amount,
                                    updated_at=CURRENT_TIMESTAMP
                                """,
                                (
                                    quote.get("ts_code"),
                                    quote.get("trade_date"),
                                    quote.get("open"),
                                    quote.get("high"),
                                    quote.get("low"),
                                    quote.get("close"),
                                    quote.get("vol"),
                                    quote.get("amount"),
                                ),
                            )

                        total_records += len(quotes)
                        conn.commit()

                    except Exception as e:
                        logger.warning(f"Failed to sync quotes for {stock_code}: {e}")
                        continue

                result["total"] = total_records
                result["inserted"] = total_records
                result["status"] = "success"
                logger.info(
                    f"Daily quotes sync completed: {total_records} records for {len(stocks)} stocks"
                )

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Daily quotes sync failed: {e}")

        return result

    def sync_fund_flow(
        self, days: Optional[int] = None, ts_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync fund flow data - incremental

        Args:
            days: Number of days to sync (defaults to config.SYNC_FUND_FLOW_DAYS)
            ts_code: Specific stock to sync (defaults to all)

        Returns:
            Sync result dictionary
        """
        days = days or config.SYNC_FUND_FLOW_DAYS
        logger.info(f"Starting fund flow sync (days={days})...")

        result = {
            "table": "fund_flow",
            "status": "pending",
            "total": 0,
            "inserted": 0,
            "updated": 0,
            "error": None,
        }

        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            with self._get_connection() as conn:
                cursor = conn.cursor()

                if ts_code:
                    cursor.execute(
                        "SELECT ts_code FROM stocks WHERE ts_code = ?", (ts_code,)
                    )
                else:
                    cursor.execute("SELECT ts_code FROM stocks")

                stocks = [row[0] for row in cursor.fetchall()]
                total_records = 0

                for stock_code in stocks:
                    try:
                        flows = self.client.get_fund_flow(stock_code, start_date, end_date)

                        for flow in flows:
                            cursor.execute(
                                """
                                INSERT INTO fund_flow 
                                (ts_code, trade_date, buy_sm_volume, buy_sm_amount, 
                                 sell_sm_volume, sell_sm_amount, net_sm_volume, net_sm_amount,
                                 buy_md_volume, buy_md_amount, sell_md_volume, sell_md_amount,
                                 net_md_volume, net_md_amount, buy_lg_volume, buy_lg_amount,
                                 sell_lg_volume, sell_lg_amount, net_lg_volume, net_lg_amount, net_inflow)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(ts_code, trade_date) DO UPDATE SET
                                    net_inflow=excluded.net_inflow,
                                    net_lg_amount=excluded.net_lg_amount,
                                    updated_at=CURRENT_TIMESTAMP
                                """,
                                (
                                    flow.get("ts_code"),
                                    flow.get("trade_date"),
                                    flow.get("buy_sm_volume"),
                                    flow.get("buy_sm_amount"),
                                    flow.get("sell_sm_volume"),
                                    flow.get("sell_sm_amount"),
                                    flow.get("net_sm_volume"),
                                    flow.get("net_sm_amount"),
                                    flow.get("buy_md_volume"),
                                    flow.get("buy_md_amount"),
                                    flow.get("sell_md_volume"),
                                    flow.get("sell_md_amount"),
                                    flow.get("net_md_volume"),
                                    flow.get("net_md_amount"),
                                    flow.get("buy_lg_volume"),
                                    flow.get("buy_lg_amount"),
                                    flow.get("sell_lg_volume"),
                                    flow.get("sell_lg_amount"),
                                    flow.get("net_lg_volume"),
                                    flow.get("net_lg_amount"),
                                    flow.get("net_inflow"),
                                ),
                            )

                        total_records += len(flows)
                        conn.commit()

                    except Exception as e:
                        logger.warning(f"Failed to sync fund flow for {stock_code}: {e}")
                        continue

                result["total"] = total_records
                result["inserted"] = total_records
                result["status"] = "success"
                logger.info(f"Fund flow sync completed: {total_records} records")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Fund flow sync failed: {e}")

        return result

    def sync_concepts(self) -> Dict[str, Any]:
        """Sync concept sectors and their stocks

        Returns:
            Sync result dictionary
        """
        logger.info("Starting concepts sync...")

        result = {
            "table": "concept_sectors",
            "status": "pending",
            "total": 0,
            "inserted": 0,
            "updated": 0,
            "error": None,
        }

        try:
            concepts = self.client.get_concept_list()
            total_records = 0

            with self._get_connection() as conn:
                cursor = conn.cursor()

                for concept in concepts:
                    concept_id = concept.get("id")
                    concept_name = concept.get("name")

                    try:
                        stocks = self.client.get_concept_stocks(concept_id)

                        for stock in stocks:
                            cursor.execute(
                                """
                                INSERT INTO concept_sectors (concept_id, concept_name, ts_code)
                                VALUES (?, ?, ?)
                                ON CONFLICT(concept_id, ts_code) DO UPDATE SET
                                    concept_name=excluded.concept_name,
                                    updated_at=CURRENT_TIMESTAMP
                                """,
                                (
                                    concept_id,
                                    concept_name,
                                    stock.get("ts_code"),
                                ),
                            )

                        total_records += len(stocks)
                        conn.commit()

                    except Exception as e:
                        logger.warning(f"Failed to sync stocks for concept {concept_id}: {e}")
                        continue

                result["total"] = total_records
                result["inserted"] = total_records
                result["status"] = "success"
                logger.info(f"Concepts sync completed: {total_records} records")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Concepts sync failed: {e}")

        return result

    def full_sync(self) -> Dict[str, Any]:
        """Execute complete synchronization pipeline

        Returns:
            Dictionary with results from all sync operations
        """
        logger.info("=" * 50)
        logger.info("Starting FULL DATA PIPELINE SYNC")
        logger.info("=" * 50)

        results = {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "syncs": {},
        }

        try:
            # Ensure database is initialized
            init_database()

            # Phase 1: Sync stocks (foundation)
            results["syncs"]["stocks"] = self.sync_stocks()

            # Phase 2: Sync daily quotes
            results["syncs"]["daily_quotes"] = self.sync_daily_quotes()

            # Phase 3: Sync fund flow
            results["syncs"]["fund_flow"] = self.sync_fund_flow()

            # Phase 4: Sync concepts
            results["syncs"]["concepts"] = self.sync_concepts()

            logger.info("=" * 50)
            logger.info("FULL SYNC COMPLETED SUCCESSFULLY")
            logger.info("=" * 50)

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            logger.error(f"Full sync failed: {e}")

        return results
