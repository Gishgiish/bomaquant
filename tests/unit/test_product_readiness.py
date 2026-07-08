from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.settings import get_settings, reset_settings_cache
from src.services.analysis_service import AnalysisService


class StubService:
    def get_stock(self, symbol: str):
        return {"symbol": symbol, "success": True}

    def get_market_summary(self):
        return {"success": True}


def build_client(tmp_path):
    storage_path = tmp_path / "analysis_jobs.sqlite3"
    persistence_service = AnalysisService(storage_path=str(storage_path))
    app = create_app(
        service_factory=lambda: StubService(),
        persistence_service=persistence_service,
    )
    return TestClient(app)


def test_profile_endpoint_creates_and_reads_profile(tmp_path):
    reset_settings_cache()
    settings = get_settings()
    settings.auth_enabled = True
    settings.api_username = "alice"
    settings.api_password = "secret"

    client = build_client(tmp_path)

    response = client.post(
        "/profiles/me",
        json={"plan": "premium", "status": "active"},
        auth=("alice", "secret"),
    )

    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    assert response.json()["plan"] == "premium"

    fetched = client.get("/profiles/me", auth=("alice", "secret"))
    assert fetched.status_code == 200
    assert fetched.json()["username"] == "alice"


def test_non_premium_user_cannot_create_portfolios(tmp_path):
    reset_settings_cache()
    settings = get_settings()
    settings.auth_enabled = True
    settings.api_username = "alice"
    settings.api_password = "secret"

    client = build_client(tmp_path)

    client.post(
        "/profiles/me",
        json={"plan": "free", "status": "active"},
        auth=("alice", "secret"),
    )

    response = client.post(
        "/portfolios",
        json={"name": "Test", "symbols": ["SCOM"]},
        auth=("alice", "secret"),
    )

    assert response.status_code == 403


def test_premium_profile_without_portfolio_feature_cannot_create_portfolios(tmp_path):
    reset_settings_cache()
    settings = get_settings()
    settings.auth_enabled = True
    settings.api_username = "alice"
    settings.api_password = "secret"

    client = build_client(tmp_path)

    client.post(
        "/profiles/me",
        json={"plan": "premium", "status": "active", "features": ["market_data"]},
        auth=("alice", "secret"),
    )

    response = client.post(
        "/portfolios",
        json={"name": "Test", "symbols": ["SCOM"]},
        auth=("alice", "secret"),
    )

    assert response.status_code == 403
