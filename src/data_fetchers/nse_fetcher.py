# src/data_fetchers/nse_fetcher.py
import time
from typing import Any, Dict, Optional

import requests

from src.config.nse_symbols import NSE_SYMBOLS, is_valid_nse_symbol
from src.data_fetchers.base_fetcher import BaseDataFetcher
from src.data_fetchers.cache_manager import CacheManager
from src.services.provider_interface import MarketDataProvider, normalize_provider_payload
from src.utils.logger import get_logger
from src.utils.validators import validate_positive_number

logger = get_logger(__name__)


class RetryConfiguration:
    def __init__(self, retries: int = 3, backoff_base_seconds: float = 0.5, backoff_factor: float = 2.0):
        self.retries = retries
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_factor = backoff_factor


class RetryableProviderError(RuntimeError):
    """Raised when a transient provider error should be retried."""


class NSEFetcher(BaseDataFetcher, MarketDataProvider):
    """Fetcher for Nairobi Securities Exchange (Kenya) data"""
    
    # API Endpoints
    RAPIDAPI_BASE = "https://nairobi-stock-exchange-nse.p.rapidapi.com"
    STOCK_ENDPOINT = "/stock/{symbol}"
    SUMMARY_ENDPOINT = "/market/summary"
    
    def __init__(
        self,
        api_key: str,
        cache: Optional[CacheManager] = None,
        timeout: int = 10,
        max_retries: int = 3,
    ):
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.api_key = api_key
        self.cache = cache or CacheManager()
        self.retry_config = RetryConfiguration(retries=max_retries, backoff_base_seconds=0.5, backoff_factor=2.0)
        self.session.headers.update(
            {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "nairobi-stock-exchange-nse.p.rapidapi.com",
            }
        )
    
    def fetch(self, symbol: str, **kwargs: Any) -> Dict[str, Any]:
        use_cache = kwargs.get("use_cache", True)
        """Fetch stock data for a given NSE symbol"""
        # 1. Validate input
        symbol = self._validate_symbol(symbol)

        # 2. Try cache first (if enabled)
        if use_cache:
            cached = self.cache.get(
                endpoint=self.STOCK_ENDPOINT.format(symbol=symbol),
                params={"symbol": symbol}
            )
            if cached:
                cached["cached"] = True
                return cached
        
        # 3. Fetch from API with retry logic
        try:
            data = self._fetch_with_retry(symbol)
            normalized = normalize_provider_payload(data, kind="stock")
            normalized["cached"] = False
            normalized["fetched_at"] = time.time()
            normalized.setdefault("success", True)
            normalized.setdefault("provider", "nse")

            data = normalized

            if use_cache:
                self.cache.set(
                    endpoint=self.STOCK_ENDPOINT.format(symbol=symbol),
                    params={"symbol": symbol},
                    data=data
                )

            self._log_api_call(self.STOCK_ENDPOINT, symbol, success=True)
            return data

        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}", exc_info=True)
            self._log_api_call(self.STOCK_ENDPOINT, symbol, success=False)
            error_type = "rate_limit_error" if "rate limit" in str(e).lower() or "429" in str(e) else "provider_error"
            return self._fallback_response(symbol, error_type, str(e))
    
    def _fetch_with_retry(self, symbol: str) -> Dict[str, Any]:
        """Internal: Fetch with exponential backoff retry."""
        last_error: Optional[Exception] = None

        for attempt in range(self.retry_config.retries):
            try:
                url = f"{self.RAPIDAPI_BASE}{self.STOCK_ENDPOINT.format(symbol=symbol)}"
                response = self.session.get(url, timeout=self.timeout)

                if response.status_code in {408, 429, 500, 502, 503, 504}:
                    raise RetryableProviderError(f"Transient API error {response.status_code}")
                if response.status_code >= 400:
                    raise RuntimeError(f"API error {response.status_code}: {response.text}")

                data = response.json()

                if "price" not in data or "symbol" not in data:
                    raise RuntimeError("Invalid API response structure")

                data["price"] = validate_positive_number(data["price"], "price")
                if "volume" in data:
                    data["volume"] = validate_positive_number(data["volume"], "volume")

                return data

            except RetryableProviderError as exc:
                last_error = exc
                if attempt < self.retry_config.retries - 1:
                    self._sleep_with_backoff(attempt)
                    continue
                raise
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retry_config.retries - 1:
                    self._sleep_with_backoff(attempt)
                    continue
                raise
            except RuntimeError as exc:
                last_error = exc
                if attempt < self.retry_config.retries - 1 and "Transient" in str(exc):
                    self._sleep_with_backoff(attempt)
                    continue
                raise

        raise last_error or RuntimeError("Unknown fetch error")
    
    def _sleep_with_backoff(self, attempt: int) -> None:
        wait = self.retry_config.backoff_base_seconds * (self.retry_config.backoff_factor ** attempt)
        time.sleep(wait)

    def _fallback_response(self, symbol: str, error_type: str, message: str, *, cached: bool = False) -> Dict[str, Any]:
        return {
            "success": False,
            "fallback": True,
            "provider": "nse",
            "symbol": symbol.upper(),
            "cached": cached,
            "error": {
                "type": error_type,
                "message": message,
                "timestamp": time.time(),
            },
        }

    def get_stock(self, symbol: str) -> Dict[str, Any]:
        return self.fetch(symbol, use_cache=True)

    def get_market_summary(self) -> Dict[str, Any]:
        return self.fetch_market_summary(use_cache=True)

    def fetch_market_summary(self, use_cache: bool = True) -> Dict[str, Any]:
        """Fetch NSE 20 Index market summary"""
        if use_cache:
            cached = self.cache.get(
                endpoint=self.SUMMARY_ENDPOINT,
                params={}
            )
            if cached:
                cached["cached"] = True
                return cached
        
        try:
            url = f"{self.RAPIDAPI_BASE}{self.SUMMARY_ENDPOINT}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            normalized = normalize_provider_payload(data, kind="market_summary")
            normalized["cached"] = False
            normalized["fetched_at"] = time.time()
            normalized.setdefault("success", True)
            normalized.setdefault("provider", "nse")
            data = normalized

            if use_cache:
                self.cache.set(
                    endpoint=self.SUMMARY_ENDPOINT,
                    params={},
                    data=data
                )

            return data

        except Exception as e:
            logger.error(f"Market summary fetch failed: {e}")
            return self._fallback_response("SUMMARY", "summary_error", str(e))
    
    def _validate_symbol(self, symbol: str) -> str:
        """Override base validation with NSE-specific rules"""
        if not symbol or not isinstance(symbol, str):
            raise ValueError(
                f"Invalid NSE symbol: {symbol}. Use: {list(NSE_SYMBOLS.keys())}"
            )

        symbol = super()._validate_symbol(symbol)
        if not is_valid_nse_symbol(symbol):
            raise ValueError(
                f"Invalid NSE symbol: '{symbol}'. "
                f"Valid examples: {list(NSE_SYMBOLS.keys())[:5]}..."
            )
        return symbol
    
    def _error_response(self, error_type: str, message: str) -> Dict[str, Any]:
        """Standardized error response structure"""
        return {
            "success": False,
            "error": {
                "type": error_type,
                "message": message,
                "timestamp": time.time()
            },
            "cached": False
        }