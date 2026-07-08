# src/data_fetchers/base_fetcher.py
from abc import ABC, abstractmethod
from typing import Any, Dict

from src.utils.logger import get_logger

logger = get_logger(__name__)

class BaseDataFetcher(ABC):
    """Abstract base class for all data fetchers (NSE, News, Sentiment, etc.)"""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._init_session()
    
    def _init_session(self):
        """Initialize requests session with best practices"""
        import requests
        session = requests.Session()
        session.headers.update({
            "User-Agent": "SokoSenseAI/1.0 (Kenya Stock Analyzer)",
            "Accept": "application/json"
        })
        return session
    
    @abstractmethod
    def fetch(self, symbol: str, **kwargs: Any) -> Dict[str, Any]:
        """Main method to fetch data for a symbol"""
        pass
    
    def _validate_symbol(self, symbol: str) -> str:
        """Common symbol validation (override if needed)"""
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        return symbol.strip().upper()
    
    def _log_api_call(self, endpoint: str, symbol: str, success: bool):
        """Secure logging (never log API keys or full responses)"""
        logger.info(
            f"API Call: {endpoint} | Symbol: {symbol} | Success: {success}",
            extra={"symbol": symbol, "endpoint": endpoint}  # Structured logging
        )