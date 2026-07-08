from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Portfolio:
    name: str
    symbols: List[str] = field(default_factory=list)

    def add_symbol(self, symbol: str) -> None:
        normalized = symbol.strip().upper()
        if normalized and normalized not in self.symbols:
            self.symbols.append(normalized)

    def remove_symbol(self, symbol: str) -> None:
        normalized = symbol.strip().upper()
        self.symbols = [item for item in self.symbols if item != normalized]

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "symbols": list(self.symbols)}


@dataclass
class Subscription:
    plan: str
    customer_id: str
    status: str = "active"
    features: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan": self.plan,
            "customer_id": self.customer_id,
            "status": self.status,
            "features": list(self.features),
        }
