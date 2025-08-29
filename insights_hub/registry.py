# insights_hub/registry.py
from __future__ import annotations
from typing import Callable, Dict, List, Any

Provider = Callable[[Dict[str, Any]], Dict[str, Any]]

_REGISTRY: List[Provider] = []

def register(provider: Provider) -> Provider:
    """Decorator to register a provider."""
    _REGISTRY.append(provider)
    return provider

def providers() -> List[Provider]:
    return list(_REGISTRY)

