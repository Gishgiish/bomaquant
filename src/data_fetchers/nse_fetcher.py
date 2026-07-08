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

            # 4. Cache successful response
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
            error_type = "rate_limit_error" if "rate limit" in str(e).lower() else "api_error"
            return self._error_response(error_type, str(e))
    
    def _fetch_with_retry(self, symbol: str) -> Dict[str, Any]:
        """Internal: Fetch with exponential backoff retry"""
        last_error = None
        
        for attempt in range(self.retry_config.retries):
            try:
                url = f"{self.RAPIDAPI_BASE}{self.STOCK_ENDPOINT.format(symbol=symbol)}"
                response = self.session.get(url, timeout=self.timeout)
                
                # Handle HTTP errors
                if response.status_code == 429:
                    raise RuntimeError("Rate limit exceeded")
                elif response.status_code >= 400:
                    raise RuntimeError(f"API error {response.status_code}: {response.text}")
                
                data = response.json()
                
                # Validate response structure (basic)
                if "price" not in data or "symbol" not in data:
                    raise RuntimeError("Invalid API response structure")
                
                # Sanitize numeric fields
                data["price"] = validate_positive_number(data["price"], "price")
                if "volume" in data:
                    data["volume"] = validate_positive_number(data["volume"], "volume")
                
                return data
                
            except requests.RequestException as e:
                last_error = e
                if attempt < self.retry_config.retries - 1:
                    wait = self.retry_config.backoff_base_seconds * (self.retry_config.backoff_factor ** attempt)
                    time.sleep(wait)
                    continue
                raise
        
        raise last_error or RuntimeError("Unknown fetch error")
    
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
            return self._error_response("summary_error", str(e))
    
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