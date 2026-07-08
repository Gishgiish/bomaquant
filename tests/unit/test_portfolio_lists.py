import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.settings import reset_settings_cache
from src.services.analysis_service import AnalysisService


class StubService:
    def get_stock(self, symbol: str):
        return {"symbol": symbol, "success": True}

    def get_market_summary(self):
        return {"success": True}


@pytest.fixture(autouse=True)
def clear_settings_cache():
    reset_settings_cache()
    yield
    reset_settings_cache()


def build_client(tmp_path):
    storage_path = tmp_path / "analysis_jobs.sqlite3"
    persistence_service = AnalysisService(storage_path=str(storage_path))
    app = create_app(
        service_factory=lambda: StubService(),
        persistence_service=persistence_service,
    )
    return TestClient(app)


def test_portfolio_listing_and_watchlist_retrieval(tmp_path):
    client = build_client(tmp_path)

    client.post("/portfolios", json={"name": "Growth", "symbols": ["SCOM"]}, auth=("admin", "change-me"))
    client.post("/watchlists/Growth/items", json={"symbol": "KCB"}, auth=("admin", "change-me"))

    portfolios_response = client.get("/portfolios", auth=("admin", "change-me"))
    assert portfolios_response.status_code == 200
    assert len(portfolios_response.json()) >= 1

    watchlist_response = client.get("/watchlists/Growth", auth=("admin", "change-me"))
    assert watchlist_response.status_code == 200
    assert watchlist_response.json()["symbols"] == ["SCOM", "KCB"]
