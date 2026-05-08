"""Multi-Factor Stock Scoring Engine

Implements Factor A (Trend & Momentum), Factor B (Capital Flow),
and Factor C (Sector & Sentiment) scoring logic.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.config import config
from src.logger import get_logger
from src.analysis.indicators import TechnicalIndicators
from src.data.tushare_client import TushareClient

logger = get_logger(__name__)


@dataclass
class StockScore:
    """Stock scoring result"""

    ts_code: str
    symbol: str
    name: str
    price: float
    factor_a_score: float  # Trend & Momentum (40%)
    factor_b_score: float  # Capital Flow (40%)
    factor_c_score: float  # Sector & Sentiment (20%)
    total_score: float
    ema20: Optional[float] = None
    ema60: Optional[float] = None
    macd: Optional[float] = None
    net_inflow: Optional[float] = None
    sector: Optional[str] = None
    calculation_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "ts_code": self.ts_code,
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "factor_a_score": round(self.factor_a_score, 2),
            "factor_b_score": round(self.factor_b_score, 2),
            "factor_c_score": round(self.factor_c_score, 2),
            "total_score": round(self.total_score, 2),
            "ema20": self.ema20,
            "ema60": self.ema60,
            "macd": self.macd,
            "net_inflow": self.net_inflow,
            "sector": self.sector,
            "calculation_date": self.calculation_date,
        }


class MultiFactorScorer:
    """Multi-factor stock scoring engine (0-100 scale)"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize scorer

        Args:
            db_path: Database path (defaults to config.DB_PATH)
        """
        self.db_path = db_path or config.DB_PATH
        self.client = TushareClient()
        logger.info("MultiFactorScorer initialized")

    def _get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _get_daily_data(
        self, ts_code: str, days: int = 60
    ) -> pd.DataFrame:
        """Get daily quote data for a stock

        Args:
            ts_code: Stock code
            days: Number of days to retrieve

        Returns:
            DataFrame with OHLCV data
        """
        conn = self._get_db_connection()
        try:
            query = f"""
            SELECT ts_code, trade_date, open, high, low, close, vol, amount
            FROM daily_quotes
            WHERE ts_code = ? AND trade_date IS NOT NULL
            ORDER BY trade_date DESC
            LIMIT {days}
            """
            df = pd.read_sql_query(query, conn, params=(ts_code,))
            df = df.sort_values("trade_date").reset_index(drop=True)
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df["high"] = pd.to_numeric(df["high"], errors="coerce")
            df["low"] = pd.to_numeric(df["low"], errors="coerce")
            df["vol"] = pd.to_numeric(df["vol"], errors="coerce")
            return df
        finally:
            conn.close()

    def _calculate_factor_a(
        self, ts_code: str
    ) -> Tuple[float, Dict[str, Any]]:
        """Calculate Factor A: Trend & Momentum (40%)

        Conditions:
        - K-line above EMA20
        - EMA20 in uptrend or just crossed above EMA60
        - MACD above zero axis

        Args:
            ts_code: Stock code

        Returns:
            Tuple of (factor_a_score, details_dict)
        """
        score = 0.0
        details = {}

        try:
            df = self._get_daily_data(ts_code, days=60)

            if df.empty or len(df) < 30:
                logger.warning(f"Insufficient data for {ts_code}")
                return 0.0, details

            # Calculate technical indicators
            close_prices = df["close"]
            ema20 = TechnicalIndicators.calculate_ema(close_prices, 20).iloc[-1]
            ema60 = TechnicalIndicators.calculate_ema(close_prices, 60).iloc[-1]
            macd, signal, hist = TechnicalIndicators.calculate_macd(close_prices)
            macd_val = macd.iloc[-1]

            current_price = close_prices.iloc[-1]
            details["current_price"] = current_price
            details["ema20"] = ema20
            details["ema60"] = ema60
            details["macd"] = macd_val

            # Scoring logic
            base_score = 0.0

            # 1. K-line above EMA20 (max 30 points)
            if current_price > ema20:
                above_ema20_pct = (current_price - ema20) / ema20 * 100
                above_ema20_score = min(30, above_ema20_pct * 3)  # Scale: 1% = 3 points
                base_score += above_ema20_score
                details["above_ema20_pct"] = round(above_ema20_pct, 2)
                details["above_ema20_score"] = round(above_ema20_score, 2)

            # 2. EMA20 in uptrend or crossing EMA60 (max 35 points)
            ema20_trend = (ema20 - ema20.iloc[-5]) / ema20.iloc[-5] * 100 if len(ema20) > 5 else 0
            if ema20_trend > 0:  # EMA20 uptrending
                ema_trend_score = min(35, abs(ema20_trend) * 5)
                base_score += ema_trend_score
                details["ema20_trend_pct"] = round(ema20_trend, 2)
                details["ema_trend_score"] = round(ema_trend_score, 2)
            elif ema20 > ema60 and ema20.iloc[-5] <= ema60.iloc[-5]:  # Recent crossover
                base_score += 30  # Golden cross
                details["golden_cross"] = True

            # 3. MACD above zero axis (max 35 points)
            if macd_val > 0:
                macd_score = min(35, macd_val * 100)  # Scale MACD value to 0-35
                base_score += macd_score
                details["macd_score"] = round(macd_score, 2)

            score = min(100, base_score)  # Cap at 100
            details["factor_a_score"] = round(score, 2)

        except Exception as e:
            logger.warning(f"Factor A calculation error for {ts_code}: {e}")
            details["error"] = str(e)

        return score, details

    def _calculate_factor_b(
        self, ts_code: str
    ) -> Tuple[float, Dict[str, Any]]:
        """Calculate Factor B: Capital Flow (40%)

        Conditions:
        - Positive net inflow in recent 5-10 trading days
        - Concentrated chips
        - North-bound fund buying (if available)

        Args:
            ts_code: Stock code

        Returns:
            Tuple of (factor_b_score, details_dict)
        """
        score = 0.0
        details = {}

        try:
            conn = self._get_db_connection()
            try:
                # Get recent fund flow (10 days)
                query = """
                SELECT trade_date, net_lg_amount, net_inflow
                FROM fund_flow
                WHERE ts_code = ? AND trade_date IS NOT NULL
                ORDER BY trade_date DESC
                LIMIT 10
                """
                df = pd.read_sql_query(query, conn, params=(ts_code,))

                if df.empty:
                    logger.debug(f"No fund flow data for {ts_code}")
                    return 0.0, details

                # Convert to numeric
                df["net_lg_amount"] = pd.to_numeric(df["net_lg_amount"], errors="coerce")
                df["net_inflow"] = pd.to_numeric(df["net_inflow"], errors="coerce")

                # Calculate cumulative net inflow (recent 5-10 days)
                cumulative_inflow = df["net_inflow"].sum()
                large_order_inflow = df["net_lg_amount"].sum()

                details["cumulative_inflow"] = round(cumulative_inflow, 2)
                details["large_order_inflow"] = round(large_order_inflow, 2)

                # Scoring logic
                base_score = 0.0

                # 1. Positive cumulative inflow (max 40 points)
                if cumulative_inflow > 0:
                    inflow_score = min(40, (cumulative_inflow / 1e8) * 10)  # Scale: 100M = 1 point
                    base_score += inflow_score
                    details["inflow_score"] = round(inflow_score, 2)

                # 2. Large order concentration (max 30 points)
                if large_order_inflow > 0:
                    large_order_ratio = large_order_inflow / cumulative_inflow if cumulative_inflow > 0 else 0
                    if large_order_ratio > 0.5:  # Large orders > 50% of total
                        concentration_score = min(30, large_order_ratio * 60)
                        base_score += concentration_score
                        details["concentration_score"] = round(concentration_score, 2)
                        details["large_order_ratio"] = round(large_order_ratio, 2)

                # 3. Consecutive positive days (max 30 points)
                positive_days = (df["net_inflow"] > 0).sum()
                if positive_days >= 5:
                    consecutive_score = min(30, positive_days * 5)
                    base_score += consecutive_score
                    details["consecutive_score"] = round(consecutive_score, 2)
                    details["positive_days"] = int(positive_days)

                score = min(100, base_score)
                details["factor_b_score"] = round(score, 2)

            finally:
                conn.close()

        except Exception as e:
            logger.warning(f"Factor B calculation error for {ts_code}: {e}")
            details["error"] = str(e)

        return score, details

    def _calculate_factor_c(
        self, ts_code: str
    ) -> Tuple[float, Dict[str, Any]]:
        """Calculate Factor C: Sector & Sentiment (20%)

        Conditions:
        - Concept sector with strong fund inflow ranking
        - Sector index in uptrend
        - Enjoy Beta premium

        Args:
            ts_code: Stock code

        Returns:
            Tuple of (factor_c_score, details_dict)
        """
        score = 0.0
        details = {}

        try:
            conn = self._get_db_connection()
            try:
                # Find sectors for this stock
                query = """
                SELECT DISTINCT concept_id, concept_name
                FROM concept_sectors
                WHERE ts_code = ?
                """
                sectors = pd.read_sql_query(query, conn, params=(ts_code,))

                if sectors.empty:
                    logger.debug(f"No sector data for {ts_code}")
                    return 0.0, details

                base_score = 0.0
                sector_scores = []

                for _, sector in sectors.iterrows():
                    concept_id = sector["concept_id"]
                    concept_name = sector["concept_name"]

                    # Get recent sector performance (5 days)
                    query = """
                    SELECT close_change_pct
                    FROM sector_daily_performance
                    WHERE concept_id = ? AND trade_date IS NOT NULL
                    ORDER BY trade_date DESC
                    LIMIT 5
                    """
                    perf = pd.read_sql_query(query, conn, params=(concept_id,))

                    if not perf.empty:
                        perf["close_change_pct"] = pd.to_numeric(
                            perf["close_change_pct"], errors="coerce"
                        )
                        avg_change = perf["close_change_pct"].mean()
                        positive_days = (perf["close_change_pct"] > 0).sum()

                        # Sector uptrend scoring (max 30 points per sector)
                        if avg_change > 0:
                            sector_score = min(30, avg_change * 10)
                            sector_scores.append(sector_score)
                            details[f"{concept_name}_trend"] = round(avg_change, 2)
                            details[f"{concept_name}_score"] = round(sector_score, 2)

                        # Bonus for consistently positive sector
                        if positive_days >= 3:
                            details[f"{concept_name}_positive_days"] = int(positive_days)
                            sector_scores.append(min(20, positive_days * 5))  # Additional bonus

                # Take average of sector scores
                if sector_scores:
                    base_score = np.mean(sector_scores)

                score = min(100, base_score)
                details["factor_c_score"] = round(score, 2)
                details["sector_count"] = len(sectors)

            finally:
                conn.close()

        except Exception as e:
            logger.warning(f"Factor C calculation error for {ts_code}: {e}")
            details["error"] = str(e)

        return score, details

    def score_stock(
        self, ts_code: str
    ) -> Optional[StockScore]:
        """Calculate composite score for a stock

        Weights:
        - Factor A (Trend & Momentum): 40%
        - Factor B (Capital Flow): 40%
        - Factor C (Sector & Sentiment): 20%

        Args:
            ts_code: Stock code

        Returns:
            StockScore object or None if calculation fails
        """
        try:
            conn = self._get_db_connection()
            try:
                # Get stock info
                query = "SELECT symbol, name FROM stocks WHERE ts_code = ?"
                stock_info = pd.read_sql_query(query, conn, params=(ts_code,))

                if stock_info.empty:
                    logger.warning(f"Stock info not found for {ts_code}")
                    return None

                symbol = stock_info.iloc[0]["symbol"]
                name = stock_info.iloc[0]["name"]

            finally:
                conn.close()

            # Get current price
            df = self._get_daily_data(ts_code, days=1)
            if df.empty:
                logger.warning(f"No price data for {ts_code}")
                return None

            current_price = df["close"].iloc[-1]
            calculation_date = df["trade_date"].iloc[-1]

            # Calculate factors
            factor_a, details_a = self._calculate_factor_a(ts_code)
            factor_b, details_b = self._calculate_factor_b(ts_code)
            factor_c, details_c = self._calculate_factor_c(ts_code)

            # Composite score (weighted average)
            total_score = factor_a * 0.4 + factor_b * 0.4 + factor_c * 0.2

            # Create StockScore object
            score_obj = StockScore(
                ts_code=ts_code,
                symbol=symbol,
                name=name,
                price=current_price,
                factor_a_score=factor_a,
                factor_b_score=factor_b,
                factor_c_score=factor_c,
                total_score=total_score,
                ema20=details_a.get("ema20"),
                ema60=details_a.get("ema60"),
                macd=details_a.get("macd"),
                net_inflow=details_b.get("cumulative_inflow"),
                calculation_date=calculation_date,
            )

            logger.info(
                f"Scored {ts_code} ({name}): Total={total_score:.2f} "
                f"(A={factor_a:.2f}, B={factor_b:.2f}, C={factor_c:.2f})"
            )

            return score_obj

        except Exception as e:
            logger.error(f"Error scoring stock {ts_code}: {e}")
            return None

    def score_top_stocks(
        self, limit: int = 50, min_score: float = 50.0
    ) -> List[StockScore]:
        """Score all stocks and return top performers

        Args:
            limit: Number of top stocks to return
            min_score: Minimum score threshold

        Returns:
            List of StockScore objects sorted by total_score descending
        """
        logger.info(f"Scoring all stocks (limit={limit}, min_score={min_score})...")

        conn = self._get_db_connection()
        try:
            # Get all stocks with recent daily data
            query = """
            SELECT DISTINCT s.ts_code
            FROM stocks s
            INNER JOIN daily_quotes dq ON s.ts_code = dq.ts_code
            WHERE dq.trade_date >= datetime('now', '-30 days')
            ORDER BY s.ts_code
            """
            stocks_df = pd.read_sql_query(query, conn)
            stocks = stocks_df["ts_code"].tolist()

        finally:
            conn.close()

        logger.info(f"Found {len(stocks)} stocks with recent data")

        scores = []
        for i, ts_code in enumerate(stocks):
            if (i + 1) % 100 == 0:
                logger.info(f"Processing {i + 1}/{len(stocks)} stocks...")

            score_obj = self.score_stock(ts_code)
            if score_obj and score_obj.total_score >= min_score:
                scores.append(score_obj)

        # Sort by total_score descending
        scores.sort(key=lambda x: x.total_score, reverse=True)

        # Return top N
        top_scores = scores[:limit]

        logger.info(
            f"Scoring completed. Found {len(top_scores)} stocks with score >= {min_score}"
        )

        return top_scores
