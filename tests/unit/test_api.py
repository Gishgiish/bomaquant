import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.settings import get_settings, reset_settings_cache
from src.services.analysis_service import AnalysisService


class StubService:
    def get_stock(self, symbol: str):
        return {
            "symbol": symbol,
            "price": 10.5,
            "currency": "KES",
            "success": True,
        }

    def get_market_summary(self):
        return {
            "index_name": "NSE 20",
            "value": 1850.45,
            "success": True,
        }


@pytest.fixture(autouse=True)
def clear_settings_cache():
    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture
def client(tmp_path):
    storage_path = tmp_path / "analysis_jobs.sqlite3"
    persistence_service = AnalysisService(storage_path=str(storage_path))
    app = create_app(
        service_factory=lambda: StubService(),
        persistence_service=persistence_service,
    )
    return TestClient(app)


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_reports_ready(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_stock_endpoint_returns_payload(client):
    response = client.get("/stocks/SCOM")

    assert response.status_code == 200
    assert response.json()["symbol"] == "SCOM"
    assert response.json()["success"] is True


def test_stock_endpoint_rejects_empty_symbol(client):
    response = client.get("/stocks/   ")

    assert response.status_code == 422
    assert response.json()["error"]["type"] == "validation_error"


def test_market_summary_endpoint_returns_payload(client):
    response = client.get("/market/summary")

    assert response.status_code == 200
    assert response.json()["index_name"] == "NSE 20"
    assert response.json()["success"] is True


def test_job_creation_and_retrieval(client):
    response = client.post(
        "/jobs",
        json={
            "title": "Market scan",
            "description": "Analyze Safaricom",
            "payload": {"symbol": "SCOM"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Market scan"
    assert body["status"] == "queued"

    job_id = body["id"]
    fetched = client.get(f"/jobs/{job_id}")

    assert fetched.status_code == 200
    assert fetched.json()["id"] == job_id
    assert fetched.json()["status"] in {"queued", "running", "completed"}


def test_completed_jobs_store_report_payload(client):
    response = client.post(
        "/jobs",
        json={
            "title": "Report run",
            "description": "Create a simple report",
            "payload": {"symbol": "SCOM"},
        },
    )

    job_id = response.json()["id"]
    fetched = client.get(f"/jobs/{job_id}")

    assert fetched.status_code == 200
    assert fetched.json()["status"] == "completed"
    assert fetched.json()["result"]["status"] == "completed"
    assert fetched.json()["report"]["job_id"] == job_id


def test_completed_jobs_include_analysis_report(client, monkeypatch):
    def fake_run_analysis(payload):
        return {
            "summary": "engine ok",
            "symbol": payload.get("symbol"),
            "engine": "stub",
        }

    monkeypatch.setattr("src.services.analysis_service.run_analysis_engine", fake_run_analysis, raising=False)

    response = client.post(
        "/jobs",
        json={
            "title": "Analysis run",
            "description": "Run engine-backed analysis",
            "payload": {"symbol": "SCOM"},
        },
    )

    job_id = response.json()["id"]
    fetched = client.get(f"/jobs/{job_id}")

    assert fetched.status_code == 200
    assert fetched.json()["report"]["analysis"]["engine"] == "stub"
    assert fetched.json()["report"]["analysis"]["symbol"] == "SCOM"


def test_protected_endpoints_require_auth(tmp_path):
    storage_path = tmp_path / "analysis_jobs.sqlite3"
    persistence_service = AnalysisService(storage_path=str(storage_path))
    app = create_app(
        service_factory=lambda: StubService(),
        persistence_service=persistence_service,
    )
    client = TestClient(app)

    response = client.get("/market/summary")
    assert response.status_code == 200

    settings = get_settings()
    settings.auth_enabled = True
    response = client.get("/market/summary")
    assert response.status_code == 401
