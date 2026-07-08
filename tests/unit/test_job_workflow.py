import threading

from src.services.job_repository import SQLiteJobRepository
from src.services.job_worker import JobWorker


def test_sqlite_job_repository_round_trips_state(tmp_path):
    repo = SQLiteJobRepository(storage_path=str(tmp_path / "jobs.sqlite3"))

    created = repo.create_job(
        title="Portfolio scan",
        description="Scan a portfolio",
        payload={"symbol": "SCOM"},
    )

    assert created["status"] == "queued"
    assert created["payload"]["symbol"] == "SCOM"

    stored = repo.get_job(created["id"])
    assert stored is not None
    assert stored["title"] == "Portfolio scan"

    repo.update_status(created["id"], "running")
    repo.complete_job(created["id"], {"status": "completed"}, {"summary": "ok"})

    completed = repo.get_job(created["id"])
    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["result"]["status"] == "completed"
    assert completed["report"]["summary"] == "ok"


def test_job_worker_dispatches_handler():
    finished = threading.Event()
    seen = {}

    def handler(job_id, payload):
        seen["job_id"] = job_id
        seen["payload"] = payload
        finished.set()

    worker = JobWorker(handler=handler)
    worker.dispatch("job-123", {"symbol": "SCOM"})

    assert finished.wait(timeout=1.0)
    assert seen["job_id"] == "job-123"
    assert seen["payload"]["symbol"] == "SCOM"
