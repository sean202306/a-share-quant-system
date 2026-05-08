"""Unit tests for technical indicators"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.indicators import TechnicalIndicators


class TestTechnicalIndicators:
    """Test technical indicators calculation"""

    @pytest.fixture
    def sample_prices(self):
        """Create sample price data for testing"""
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        return pd.Series(prices)

    def test_ema_calculation(self, sample_prices):
        """Test EMA calculation"""
        ema = TechnicalIndicators.calculate_ema(sample_prices, period=20)

        assert len(ema) == len(sample_prices)
        assert ema.isna().sum() > 0  # First values should be NaN
        assert ema.iloc[-1] > 0  # Last value should be positive

    def test_macd_calculation(self, sample_prices):
        """Test MACD calculation"""
        macd, signal, histogram = TechnicalIndicators.calculate_macd(sample_prices)

        assert len(macd) == len(sample_prices)
        assert len(signal) == len(sample_prices)
        assert len(histogram) == len(sample_prices)

        # Histogram = MACD - Signal
        np.testing.assert_array_almost_equal(
            histogram[20:].values, (macd[20:] - signal[20:]).values, decimal=5
        )

    def test_rsi_calculation(self, sample_prices):
        """Test RSI calculation"""
        rsi = TechnicalIndicators.calculate_rsi(sample_prices, period=14)

        assert len(rsi) == len(sample_prices)
        # RSI should be between 0 and 100 (excluding NaN)
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_atr_calculation(self, sample_prices):
        """Test ATR calculation"""
        high = sample_prices + 2
        low = sample_prices - 2

        atr = TechnicalIndicators.calculate_atr(high, low, sample_prices, period=14)

        assert len(atr) == len(sample_prices)
        # ATR should be positive
        valid_atr = atr.dropna()
        assert (valid_atr >= 0).all()

    def test_bollinger_bands_calculation(self, sample_prices):
        """Test Bollinger Bands calculation"""
        middle, upper, lower = TechnicalIndicators.calculate_bollinger_bands(
            sample_prices, period=20
        )

        assert len(middle) == len(sample_prices)
        assert len(upper) == len(sample_prices)
        assert len(lower) == len(sample_prices)

        # Upper should be above middle, middle above lower
        valid_idx = ~middle.isna()
        assert (upper[valid_idx] >= middle[valid_idx]).all()
        assert (middle[valid_idx] >= lower[valid_idx]).all()

    def test_momentum_calculation(self, sample_prices):
        """Test Momentum calculation"""
        momentum = TechnicalIndicators.calculate_momentum(sample_prices, period=10)

        assert len(momentum) == len(sample_prices)
        # Momentum at index 10 should be price[10] - price[0]
        assert abs(momentum.iloc[10] - (sample_prices.iloc[10] - sample_prices.iloc[0])) < 0.01

    def test_rate_of_change_calculation(self, sample_prices):
        """Test ROC calculation"""
        roc = TechnicalIndicators.calculate_rate_of_change(sample_prices, period=10)

        assert len(roc) == len(sample_prices)
        # ROC values should not be extreme (reasonable range)
        valid_roc = roc.dropna()
        assert (valid_roc.abs() < 1000).all()  # Reasonable range
