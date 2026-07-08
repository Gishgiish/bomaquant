from typing import Any, Dict, Optional

from src.config.settings import get_settings
from src.data_fetchers.nse_fetcher import NSEFetcher
from src.services.provider_interface import MarketDataProvider


class MarketService(MarketDataProvider):
    def __init__(self, provider: Optional[MarketDataProvider] = None):
        self.provider = provider or self._build_provider()

    def _build_provider(self) -> MarketDataProvider:
        settings = get_settings()
        return NSEFetcher(
            api_key=settings.nse_rapidapi_key,
            timeout=settings.nse_api_timeout,
            max_retries=settings.nse_max_retries,
        )

    def get_stock(self, symbol: str) -> Dict[str, Any]:
        return self.provider.get_stock(symbol)

    def get_market_summary(self) -> Dict[str, Any]:
        return self.provider.get_market_summary()
