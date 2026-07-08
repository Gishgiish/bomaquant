from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


class JobRepository(Protocol):
    def initialize(self) -> None:
        ...

    def create_job(self, title: str, description: Optional[str], payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        ...

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        ...

    def get_job_payload(self, job_id: str) -> Dict[str, Any]:
        ...

    def update_status(self, job_id: str, status: str) -> None:
        ...

    def complete_job(self, job_id: str, result_payload: Dict[str, Any], report: Dict[str, Any]) -> None:
        ...

    def fail_job(self, job_id: str, error_message: str) -> None:
        ...


class SQLiteJobRepository:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "data/analysis_jobs.sqlite3")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
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
                    self._dump_json(payload or {}),
                    None,
                    None,
                    "queued",
                    now,
                    now,
                ),
            )
            connection.commit()

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
        with sqlite3.connect(self.storage_path) as connection:
            row = connection.execute(
                "SELECT id, title, description, payload, result, report, status, created_at, updated_at "
                "FROM analysis_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def get_job_payload(self, job_id: str) -> Dict[str, Any]:
        with sqlite3.connect(self.storage_path) as connection:
            row = connection.execute(
                "SELECT payload FROM analysis_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

        if row is None:
            return {}
        return self._load_json(row[0])

    def update_status(self, job_id: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                "UPDATE analysis_jobs SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, job_id),
            )
            connection.commit()

    def complete_job(self, job_id: str, result_payload: Dict[str, Any], report: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                "UPDATE analysis_jobs SET result = ?, report = ?, status = ?, updated_at = ? WHERE id = ?",
                (self._dump_json(result_payload), self._dump_json(report), "completed", now, job_id),
            )
            connection.commit()

    def fail_job(self, job_id: str, error_message: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        result_payload = {"status": "failed", "error": error_message}
        report = {"summary": "analysis failed", "job_id": job_id, "error": error_message}
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                "UPDATE analysis_jobs SET result = ?, report = ?, status = ?, updated_at = ? WHERE id = ?",
                (self._dump_json(result_payload), self._dump_json(report), "failed", now, job_id),
            )
            connection.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "payload": self._load_json(row[3]),
            "result": self._load_json(row[4]),
            "report": self._load_json(row[5]),
            "status": row[6],
            "created_at": row[7],
            "updated_at": row[8],
        }

    def _load_json(self, value: Optional[str]) -> Any:
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def _dump_json(self, value: Any) -> str:
        return json.dumps(value)
