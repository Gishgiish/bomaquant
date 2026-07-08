from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class AuditService:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "data/audit.sqlite3")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def record(self, actor: str, action: str, target_type: str, target_id: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = details or {}
        now = self._now()
        with sqlite3.connect(self.storage_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO audit_logs (actor, action, target_type, target_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (actor, action, target_type, target_id, json.dumps(payload), now),
            )
            connection.commit()
        return {
            "id": cursor.lastrowid,
            "actor": actor,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "details": payload,
            "created_at": now,
        }

    def list_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.storage_path) as connection:
            rows = connection.execute(
                "SELECT id, actor, action, target_type, target_id, details, created_at FROM audit_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "actor": row[1],
                "action": row[2],
                "target_type": row[3],
                "target_id": row[4],
                "details": json.loads(row[5] or "{}"),
                "created_at": row[6],
            }
            for row in rows
        ]

    def _now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
