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


def test_portfolio_crud_and_watchlist_flow(tmp_path):
    client = build_client(tmp_path)

    create_response = client.post(
        "/portfolios",
        json={"name": "Growth", "symbols": ["SCOM"]},
        auth=("admin", "change-me"),
    )
    assert create_response.status_code == 200

    update_response = client.put(
        "/portfolios/Growth",
        json={"name": "Growth", "symbols": ["SCOM", "EQTY"]},
        auth=("admin", "change-me"),
    )
    assert update_response.status_code == 200
    assert update_response.json()["symbols"] == ["SCOM", "EQTY"]

    fetch_response = client.get("/portfolios/Growth", auth=("admin", "change-me"))
    assert fetch_response.status_code == 200
    assert fetch_response.json()["symbols"] == ["SCOM", "EQTY"]

    watchlist_response = client.post(
        "/watchlists/Growth/items",
        json={"symbol": "KCB"},
        auth=("admin", "change-me"),
    )
    assert watchlist_response.status_code == 200
    assert watchlist_response.json()["symbols"] == ["SCOM", "EQTY", "KCB"]


def test_audit_log_records_create_and_update_events(tmp_path):
    client = build_client(tmp_path)

    client.post(
        "/portfolios",
        json={"name": "Audit", "symbols": ["SCOM"]},
        auth=("admin", "change-me"),
    )
    client.put(
        "/portfolios/Audit",
        json={"name": "Audit", "symbols": ["SCOM", "KCB"]},
        auth=("admin", "change-me"),
    )

    audit_response = client.get("/audit/logs", auth=("admin", "change-me"))
    assert audit_response.status_code == 200
    assert len(audit_response.json()) >= 2
