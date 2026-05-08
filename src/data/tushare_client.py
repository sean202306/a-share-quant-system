"""Tushare API Client with Exponential Backoff Retry Mechanism

Provides robust API access to Tushare Pro with automatic retry,
rate limiting, and error handling.
"""

import time
import requests
from typing import Any, Optional, List, Dict
from datetime import datetime, timedelta

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded"""
    pass


class TushareClient:
    """Tushare Pro API client with exponential backoff retry"""

    def __init__(self, token: Optional[str] = None):
        """Initialize Tushare client

        Args:
            token: Tushare Pro API token (defaults to config.TUSHARE_TOKEN)
        """
        self.token = token or config.TUSHARE_TOKEN
        self.base_url = config.TUSHARE_BASE_URL
        self.max_retries = config.MAX_RETRIES
        self.backoff_factor = config.RETRY_BACKOFF_FACTOR
        self.timeout = config.REQUEST_TIMEOUT
        self.rate_limit_delay = config.RATE_LIMIT_DELAY

        if not self.token:
            raise ValueError("Tushare token is required")

        logger.info("Tushare client initialized")

    def _request(
        self,
        api: str,
        params: Dict[str, Any],
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """Make API request with exponential backoff retry

        Args:
            api: API name (e.g., 'stock_basic')
            params: Request parameters
            retry_count: Current retry attempt count

        Returns:
            API response data

        Raises:
            RateLimitError: If rate limit exceeded after max retries
            requests.RequestException: If request fails
        """
        # Add token to params
        request_params = {"api_name": api, "token": self.token, **params}

        try:
            # Rate limiting delay
            time.sleep(self.rate_limit_delay)

            response = requests.post(
                self.base_url,
                json=request_params,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if data.get("code") != 0:
                error_msg = data.get("msg", "Unknown error")

                # Handle rate limit error
                if "超过访问频率限制" in error_msg or "超过" in error_msg:
                    if retry_count < self.max_retries:
                        wait_time = self.backoff_factor ** retry_count
                        logger.warning(
                            f"Rate limit hit. Retrying in {wait_time}s "
                            f"(attempt {retry_count + 1}/{self.max_retries})"
                        )
                        time.sleep(wait_time)
                        return self._request(api, params, retry_count + 1)
                    else:
                        raise RateLimitError(
                            f"Rate limit exceeded after {self.max_retries} retries: {error_msg}"
                        )

                # Handle other API errors
                raise ValueError(f"API error [{data.get('code')}]: {error_msg}")

            logger.debug(f"API {api} successful: {len(data.get('data', []))} records")
            return data.get("data", [])

        except requests.exceptions.Timeout:
            if retry_count < self.max_retries:
                wait_time = self.backoff_factor ** retry_count
                logger.warning(
                    f"Request timeout. Retrying in {wait_time}s "
                    f"(attempt {retry_count + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)
                return self._request(api, params, retry_count + 1)
            else:
                logger.error(f"Request timeout after {self.max_retries} retries")
                raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise

    def get_stocks(self, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get stock list

        Args:
            exchange: Exchange code (SSE, SZSE, BSE)

        Returns:
            List of stock information
        """
        params = {"fields": "ts_code,symbol,name,area,industry,market,list_date"}
        if exchange:
            params["exchange"] = exchange

        logger.info(f"Fetching stocks (exchange={exchange})")
        return self._request("stock_basic", params)

    def get_daily_quotes(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily quotes (OHLCV data)

        Args:
            ts_code: Stock code (e.g., '000001.SZ')
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)

        Returns:
            List of daily quote records
        """
        params = {
            "ts_code": ts_code,
            "fields": "ts_code,trade_date,open,high,low,close,vol,amount",
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        logger.info(f"Fetching daily quotes for {ts_code}")
        return self._request("daily", params)

    def get_fund_flow(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get fund flow data (资金流向)

        Args:
            ts_code: Stock code (e.g., '000001.SZ')
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)

        Returns:
            List of fund flow records
        """
        params = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        logger.info(f"Fetching fund flow for {ts_code}")
        return self._request("moneyflow", params)

    def get_concept_list(self) -> List[Dict[str, Any]]:
        """Get concept sector list

        Returns:
            List of concept information
        """
        logger.info("Fetching concept list")
        return self._request("concept", {})

    def get_concept_stocks(
        self, concept_id: str
    ) -> List[Dict[str, Any]]:
        """Get stocks in a concept

        Args:
            concept_id: Concept ID

        Returns:
            List of stocks in the concept
        """
        params = {"id": concept_id}
        logger.info(f"Fetching stocks for concept {concept_id}")
        return self._request("concept_detail", params)

    def get_concept_daily(
        self,
        concept_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily performance of a concept

        Args:
            concept_id: Concept ID
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)

        Returns:
            List of daily concept performance records
        """
        params = {"id": concept_id}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        logger.info(f"Fetching daily concept data for {concept_id}")
        return self._request("concept_daily", params)

    def get_north_fund_holdings(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get north bound fund (北向资金) holdings

        Args:
            ts_code: Stock code
            trade_date: Trade date (YYYYMMDD format)

        Returns:
            List of north fund holding records
        """
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date

        logger.info(f"Fetching north fund holdings (ts_code={ts_code})")
        return self._request("hsgt_detail", params)
