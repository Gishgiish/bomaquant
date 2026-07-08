from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


class DomainRepository(Protocol):
    def create_portfolio(self, name: str, symbols: Optional[list[str]] = None) -> Dict[str, Any]:
        ...

    def update_portfolio(self, name: str, symbols: Optional[list[str]] = None) -> Dict[str, Any]:
        ...

    def list_portfolios(self) -> list[Dict[str, Any]]:
        ...

    def get_portfolio(self, name: str) -> Optional[Dict[str, Any]]:
        ...

    def create_subscription(self, plan: str, customer_id: str, status: str = "active", features: Optional[list[str]] = None) -> Dict[str, Any]:
        ...

    def get_subscription(self, customer_id: str) -> Optional[Dict[str, Any]]:
        ...


class SQLiteDomainRepository:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "data/domain_store.sqlite3")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolios (
                    name TEXT PRIMARY KEY,
                    symbols TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    customer_id TEXT PRIMARY KEY,
                    plan TEXT NOT NULL,
                    status TEXT NOT NULL,
                    features TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def create_portfolio(self, name: str, symbols: Optional[list[str]] = None) -> Dict[str, Any]:
        normalized_symbols = list(symbols or [])
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO portfolios (name, symbols, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(normalized_symbols), self._now()),
            )
            connection.commit()
        return {"name": name, "symbols": normalized_symbols}

    def update_portfolio(self, name: str, symbols: Optional[list[str]] = None) -> Dict[str, Any]:
        normalized_symbols = list(symbols or [])
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO portfolios (name, symbols, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(normalized_symbols), self._now()),
            )
            connection.commit()
        return {"name": name, "symbols": normalized_symbols}

    def list_portfolios(self) -> list[Dict[str, Any]]:
        with sqlite3.connect(self.storage_path) as connection:
            rows = connection.execute("SELECT name, symbols FROM portfolios ORDER BY name").fetchall()
        return [{"name": row[0], "symbols": json.loads(row[1] or "[]")} for row in rows]

    def get_portfolio(self, name: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.storage_path) as connection:
            row = connection.execute("SELECT name, symbols FROM portfolios WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        return {"name": row[0], "symbols": json.loads(row[1] or "[]")}

    def create_subscription(self, plan: str, customer_id: str, status: str = "active", features: Optional[list[str]] = None) -> Dict[str, Any]:
        normalized_features = list(features or [])
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO subscriptions (customer_id, plan, status, features, created_at) VALUES (?, ?, ?, ?, ?)",
                (customer_id, plan, status, json.dumps(normalized_features), self._now()),
            )
            connection.commit()
        return {
            "plan": plan,
            "customer_id": customer_id,
            "status": status,
            "features": normalized_features,
        }

    def get_subscription(self, customer_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.storage_path) as connection:
            row = connection.execute(
                "SELECT customer_id, plan, status, features FROM subscriptions WHERE customer_id = ?",
                (customer_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "plan": row[1],
            "customer_id": row[0],
            "status": row[2],
            "features": json.loads(row[3] or "[]"),
        }

    def _now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
