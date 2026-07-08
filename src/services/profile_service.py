from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional


class ProfileService:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "data/profiles.sqlite3")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    username TEXT PRIMARY KEY,
                    plan TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor = connection.execute("PRAGMA table_info(profiles)")
            columns = {row[1] for row in cursor.fetchall()}
            if "features" not in columns:
                connection.execute("ALTER TABLE profiles ADD COLUMN features TEXT NOT NULL DEFAULT '[]'")
            connection.commit()

    def upsert_profile(self, username: str, plan: str, status: str, features: Optional[list[str]] = None) -> Dict[str, Any]:
        now = self._now()
        features_payload = json.dumps(features or [])
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                """
                INSERT INTO profiles (username, plan, status, features, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    plan = excluded.plan,
                    status = excluded.status,
                    features = excluded.features,
                    updated_at = excluded.updated_at
                """,
                (username, plan, status, features_payload, now, now),
            )
            connection.commit()
        return {"username": username, "plan": plan, "status": status, "features": features or []}

    def get_profile(self, username: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.storage_path) as connection:
            row = connection.execute(
                "SELECT username, plan, status, features FROM profiles WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return None
        return {
            "username": row[0],
            "plan": row[1],
            "status": row[2],
            "features": json.loads(row[3] or "[]"),
        }

    def can_access_portfolios(self, username: str) -> bool:
        profile = self.get_profile(username)
        if profile is None:
            return False
        if profile.get("plan") not in {"premium", "enterprise"}:
            return False
        features = set(profile.get("features", []))
        return "portfolio_management" in features or "portfolios" in features

    def _now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
