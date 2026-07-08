from __future__ import annotations

from typing import Any, Dict, Optional

from src.services.domain_repository import DomainRepository


class DomainService:
    def __init__(self, repository: Optional[DomainRepository] = None):
        self.repository = repository

    def create_portfolio(self, name: str, symbols: Optional[list[str]] = None) -> Dict[str, Any]:
        if self.repository is None:
            raise RuntimeError("repository not configured")
        return self.repository.create_portfolio(name, symbols)

    def update_portfolio(self, name: str, symbols: Optional[list[str]] = None) -> Dict[str, Any]:
        if self.repository is None:
            raise RuntimeError("repository not configured")
        return self.repository.update_portfolio(name, symbols)

    def list_portfolios(self) -> list[Dict[str, Any]]:
        if self.repository is None:
            raise RuntimeError("repository not configured")
        return self.repository.list_portfolios()

    def get_portfolio(self, name: str) -> Optional[Dict[str, Any]]:
        if self.repository is None:
            raise RuntimeError("repository not configured")
        return self.repository.get_portfolio(name)

    def create_subscription(self, plan: str, customer_id: str, status: str = "active", features: Optional[list[str]] = None) -> Dict[str, Any]:
        if self.repository is None:
            raise RuntimeError("repository not configured")
        return self.repository.create_subscription(plan, customer_id, status=status, features=features)

    def get_subscription(self, customer_id: str) -> Optional[Dict[str, Any]]:
        if self.repository is None:
            raise RuntimeError("repository not configured")
        return self.repository.get_subscription(customer_id)
