import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def run_analysis_engine(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Small bridge to the analysis engine for local and test usage."""
    try:
        from src.analysis_engine.analyzer_service import analyze_stock
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
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "data/analysis_jobs.sqlite3")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    payload TEXT,
                    result TEXT,
                    report TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def create_job(self, title: str, description: Optional[str], payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                """
                INSERT INTO analysis_jobs (
                    id, title, description, payload, result, report, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    title,
                    description,
                    json.dumps(payload or {}),
                    None,
                    None,
                    "queued",
                    now,
                    now,
                ),
            )
            connection.commit()

        self._dispatch_job(job_id)

        return {
            "id": job_id,
            "title": title,
            "description": description,
            "payload": payload or {},
            "result": None,
            "report": None,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
        }

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        for _ in range(10):
            with sqlite3.connect(self.storage_path) as connection:
                row = connection.execute(
                    "SELECT id, title, description, payload, result, report, status, created_at, updated_at "
                    "FROM analysis_jobs WHERE id = ?",
                    (job_id,),
                ).fetchone()

            if row is None:
                return None

            status = row[6]
            if status in {"completed", "failed"}:
                return {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "payload": json.loads(row[3] or "{}"),
                    "result": json.loads(row[4] or "null") if row[4] else None,
                    "report": json.loads(row[5] or "null") if row[5] else None,
                    "status": status,
                    "created_at": row[7],
                    "updated_at": row[8],
                }

            time.sleep(0.02)

        with sqlite3.connect(self.storage_path) as connection:
            row = connection.execute(
                "SELECT id, title, description, payload, result, report, status, created_at, updated_at "
                "FROM analysis_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "payload": json.loads(row[3] or "{}"),
            "result": json.loads(row[4] or "null") if row[4] else None,
            "report": json.loads(row[5] or "null") if row[5] else None,
            "status": row[6],
            "created_at": row[7],
            "updated_at": row[8],
        }

    def _dispatch_job(self, job_id: str) -> None:
        thread = threading.Thread(target=self._process_job, args=(job_id,), daemon=True)
        thread.start()

    def _process_job(self, job_id: str) -> None:
        self._update_status(job_id, "running")
        time.sleep(0.05)
        payload = self._get_job_payload(job_id)
        analysis = run_analysis_engine(payload)
        report = {
            "summary": "analysis completed",
            "job_id": job_id,
            "payload": payload,
            "analysis": analysis,
        }
        self._complete_job(job_id, report)

    def _complete_job(self, job_id: str, report: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        result_payload = {"status": "completed", "report_id": job_id}
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                "UPDATE analysis_jobs SET result = ?, report = ?, status = ?, updated_at = ? "
                "WHERE id = ?",
                (json.dumps(result_payload), json.dumps(report), "completed", now, job_id),
            )
            connection.commit()

    def _get_job_payload(self, job_id: str) -> Dict[str, Any]:
        with sqlite3.connect(self.storage_path) as connection:
            row = connection.execute(
                "SELECT payload FROM analysis_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return {}
        return json.loads(row[0] or "{}")

    def _update_status(self, job_id: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                "UPDATE analysis_jobs SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, job_id),
            )
            connection.commit()
