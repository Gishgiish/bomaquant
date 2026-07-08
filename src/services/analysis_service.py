import time
from importlib import import_module
from typing import Any, Dict, Optional

from src.services.job_repository import SQLiteJobRepository
from src.services.job_worker import JobWorker


def _load_analysis_function():
    for module_name in (
        "src.analysis_engine.src.services.analyzer_service",
        "src.analysis_engine.analyzer_service",
    ):
        try:
            module = import_module(module_name)
        except Exception:
            continue

        analyze_stock = getattr(module, "analyze_stock", None)
        if callable(analyze_stock):
            return analyze_stock

    raise ImportError("analysis engine module is unavailable")


def run_analysis_engine(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Small bridge to the analysis engine for local and test usage."""
    try:
        analyze_stock = _load_analysis_function()
    except Exception:
        return {"status": "unavailable", "message": "analysis engine unavailable"}

    symbol = (payload or {}).get("symbol")
    if not symbol:
        return {"status": "unavailable", "message": "symbol missing"}

    result = analyze_stock(str(symbol))
    if result is None:
        return {"status": "unavailable", "message": "analysis engine returned no result"}

    return {
        "status": "completed",
        "symbol": str(symbol),
        "summary": getattr(result, "summary", None),
    }


class AnalysisService:
    def __init__(self, storage_path: Optional[str] = None, repository=None, worker=None):
        self.repository = repository or SQLiteJobRepository(storage_path=storage_path)
        self.worker = worker or JobWorker(handler=self._process_job)

    def create_job(self, title: str, description: Optional[str], payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        job = self.repository.create_job(title, description, payload)
        self._dispatch_job(job["id"])
        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        for _ in range(10):
            job = self.repository.get_job(job_id)
            if job is None:
                return None
            if job["status"] in {"completed", "failed"}:
                return job
            time.sleep(0.02)

        return self.repository.get_job(job_id)

    def _dispatch_job(self, job_id: str) -> None:
        payload = self.repository.get_job_payload(job_id)
        self.worker.dispatch(job_id, payload)

    def _process_job(self, job_id: str, payload: Dict[str, Any]) -> None:
        self.repository.update_status(job_id, "running")
        time.sleep(0.05)
        try:
            analysis = run_analysis_engine(payload)
            report = {
                "summary": "analysis completed",
                "job_id": job_id,
                "payload": payload,
                "analysis": analysis,
            }
            self.repository.complete_job(job_id, {"status": "completed", "report_id": job_id}, report)
        except Exception as exc:
            self.repository.fail_job(job_id, str(exc))
