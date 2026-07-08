from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, factory: Callable[..., Any]) -> None:
        self._providers[name] = factory

    def get_provider(self, name: str, *, settings: Optional[Any] = None) -> Any:
        factory = self._providers.get(name)
        if factory is None:
            raise KeyError(f"Unknown provider: {name}")
        return factory(settings=settings)

    def list_providers(self) -> List[str]:
        return sorted(self._providers)
