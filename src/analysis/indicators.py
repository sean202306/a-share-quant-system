"""Technical Indicators Calculation Module

Computes EMA, MACD, RSI, and other technical indicators.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional
from src.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """Technical indicators calculator"""

    @staticmethod
    def calculate_ema(
        data: pd.Series,
        period: int,
        adjust: bool = False,
    ) -> pd.Series:
        """Calculate Exponential Moving Average (EMA)

        Args:
            data: Price series (usually close prices)
            period: Period for EMA calculation
            adjust: If False, use recursive form; if True, use adjust=True pandas method

        Returns:
            EMA series
        """
        return data.ewm(span=period, adjust=adjust).mean()

    @staticmethod
    def calculate_macd(
        data: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)

        Args:
            data: Price series
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line EMA period

        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        ema_fast = data.ewm(span=fast_period, adjust=False).mean()
        ema_slow = data.ewm(span=slow_period, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_rsi(
        data: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """Calculate Relative Strength Index (RSI)

        Args:
            data: Price series
            period: RSI period

        Returns:
            RSI series (0-100)
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """Calculate Average True Range (ATR)

        Args:
            high: High price series
            low: Low price series
            close: Close price series
            period: ATR period

        Returns:
            ATR series
        """
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands

        Args:
            data: Price series
            period: Moving average period
            std_dev: Standard deviation multiplier

        Returns:
            Tuple of (Middle band, Upper band, Lower band)
        """
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return middle, upper, lower

    @staticmethod
    def calculate_momentum(
        data: pd.Series,
        period: int = 10,
    ) -> pd.Series:
        """Calculate Price Momentum

        Args:
            data: Price series
            period: Momentum period

        Returns:
            Momentum series
        """
        return data.diff(period)

    @staticmethod
    def calculate_rate_of_change(
        data: pd.Series,
        period: int = 10,
    ) -> pd.Series:
        """Calculate Rate of Change (ROC)

        Args:
            data: Price series
            period: ROC period

        Returns:
            ROC series (percentage)
        """
        roc = ((data - data.shift(period)) / data.shift(period)) * 100
        return roc
