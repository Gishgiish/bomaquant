# tests/unit/test_nse_fetcher.py
from datetime import datetime

import pytest
import requests
import requests_mock

from src.config.settings import get_settings
from src.data_fetchers.cache_manager import CacheManager
from src.data_fetchers.nse_fetcher import NSEFetcher


@pytest.fixture
def settings(monkeypatch):
    """Mock settings for tests"""
    monkeypatch.setenv("NSE_RAPIDAPI_KEY", "test_key_12345678901234567890")
    return get_settings()

@pytest.fixture
def fetcher(settings, tmp_path):
    """Fixture: fresh fetcher with test cache"""
    cache = CacheManager(cache_dir=str(tmp_path / "cache"), ttl_seconds=300)
    return NSEFetcher(
        api_key=settings.nse_rapidapi_key,
        cache=cache,
        timeout=settings.nse_api_timeout,
        max_retries=settings.nse_max_retries
    )

def test_fetcher_validates_symbol(fetcher):
    """Test that invalid symbols raise error"""
    with pytest.raises(ValueError, match="Invalid NSE symbol"):
        fetcher.fetch("")  # Empty symbol
    
    with pytest.raises(ValueError, match="Invalid NSE symbol"):
        fetcher.fetch("INVALID_SYMBOL_123")  # Not in known list

def test_fetch_stock_price_mock_success(fetcher):
    """Test successful price fetch with mocked API"""
    symbol = "SCOM"
    mock_response = {
        "symbol": "SCOM",
        "name": "Safaricom PLC",
        "price": 28.50,
        "currency": "KES",
        "change_percent": 1.2,
        "volume": 1250000,
        "timestamp": datetime.now().isoformat()
    }
    
    with requests_mock.Mocker() as m:
        m.get(
            "https://nairobi-stock-exchange-nse.p.rapidapi.com/stock/SCOM",
            json=mock_response,
            status_code=200,
            headers={"X-RateLimit-Remaining": "99"}
        )
        
        result = fetcher.fetch(symbol)
        
        assert result["symbol"] == "SCOM"
        assert result["price"] == 28.50
        assert result["currency"] == "KES"
        assert "fetched_at" in result  # Added by fetcher

def test_fetch_stock_price_uses_cache(fetcher):
    """Test that repeated calls use cache, not API"""
    symbol = "EQTY"
    cached_data = {"symbol": "EQTY", "price": 45.00, "cached": True}
    
    # Pre-populate cache
    fetcher.cache.set(
        endpoint="/stock/EQTY",
        params={"symbol": "EQTY"},
        data=cached_data
    )
    
    # Mock API should NOT be called
    with requests_mock.Mocker() as m:
        m.get(
            "https://nairobi-stock-exchange-nse.p.rapidapi.com/stock/EQTY",
            status_code=400  # Would fail if called
        )
        
        result = fetcher.fetch(symbol)
        
        assert result["price"] == 45.00
        assert result["cached"] is True
        assert m.call_count == 0  # API never called

def test_fetch_handles_api_error(fetcher):
    """Test graceful handling of API failures"""
    symbol = "KCB"
    
    with requests_mock.Mocker() as m:
        m.get(
            "https://nairobi-stock-exchange-nse.p.rapidapi.com/stock/KCB",
            status_code=429,  # Rate limited
            json={"error": "Rate limit exceeded"}
        )
        
        result = fetcher.fetch(symbol)
        
        # Should return error structure, not crash
        assert result["error"] is not None
        assert "rate_limit" in result["error"]["type"]
        assert result["success"] is False


def test_fetch_retries_transient_errors(fetcher):
    """Transient failures should be retried and eventually succeed."""
    symbol = "SCOM"
    mock_response = {
        "symbol": "SCOM",
        "name": "Safaricom PLC",
        "price": 30.0,
        "currency": "KES",
        "change_percent": 1.5,
        "volume": 2000000,
        "timestamp": datetime.now().isoformat(),
    }

    with requests_mock.Mocker() as m:
        m.get(
            "https://nairobi-stock-exchange-nse.p.rapidapi.com/stock/SCOM",
            [
                {"exc": requests.ConnectionError("temporary outage")},
                {"json": mock_response, "status_code": 200},
            ],
        )

        result = fetcher.fetch(symbol)

        assert result["success"] is True
        assert result["price"] == 30.0
        assert m.call_count == 2


def test_fetch_returns_fallback_payload_after_retries(fetcher):
    """Exhausted retries should return a structured fallback payload."""
    symbol = "KCB"

    with requests_mock.Mocker() as m:
        m.get(
            "https://nairobi-stock-exchange-nse.p.rapidapi.com/stock/KCB",
            [{"exc": requests.Timeout("slow upstream")}, {"exc": requests.Timeout("slow upstream")}, {"exc": requests.Timeout("slow upstream")}],
        )

        result = fetcher.fetch(symbol)

        assert result["success"] is False
        assert result["fallback"] is True
        assert result["symbol"] == "KCB"
        assert result["error"]["type"] == "provider_error"


def test_fetch_market_summary(fetcher):
    """Test fetching NSE 20 Index summary"""
    mock_summary = {
        "index_name": "NSE 20",
        "value": 1850.45,
        "change_percent": 0.8,
        "volume": 45000000,
        "advancers": 12,
        "decliners": 6,
        "unchanged": 2
    }
    
    with requests_mock.Mocker() as m:
        m.get(
            "https://nairobi-stock-exchange-nse.p.rapidapi.com/market/summary",
            json=mock_summary,
            status_code=200
        )
        
        result = fetcher.fetch_market_summary()
        
        assert result["index_name"] == "NSE 20"
        assert result["value"] == 1850.45
        assert result["success"] is True