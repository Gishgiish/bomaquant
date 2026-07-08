from abc import ABC, abstractmethod
from typing import Any, Dict


def normalize_provider_payload(payload: Dict[str, Any], *, kind: str) -> Dict[str, Any]:
    """Normalize provider payloads into a consistent shape for the backend."""
    if not isinstance(payload, dict):
        return {"success": False, "error": {"type": "provider_error", "message": "invalid payload"}}

    normalized = dict(payload)
    normalized.setdefault("success", True)
    normalized.setdefault("provider", "unknown")

    if kind == "stock":
        symbol = payload.get("symbol") or payload.get("ticker")
        if isinstance(symbol, str) and symbol:
            normalized["symbol"] = symbol.upper()
    elif kind == "market_summary":
        normalized.setdefault("market", "NSE")

    return normalized


class MarketDataProvider(ABC):
    """Minimal abstraction for market data providers."""

    @abstractmethod
    def get_stock(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_market_summary(self) -> Dict[str, Any]:
        raise NotImplementedError
