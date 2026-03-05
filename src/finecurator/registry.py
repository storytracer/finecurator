"""Global adapter registry for dynamic lookup by name."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finecurator.adapters.base import BaseAdapter

_registry: dict[str, type[BaseAdapter]] = {}


def register(name: str, adapter_cls: type[BaseAdapter]) -> None:
    """Register an adapter class under the given name."""
    if name in _registry:
        raise ValueError(f"Adapter already registered: {name!r}")
    _registry[name] = adapter_cls


def get_adapter(name: str) -> type[BaseAdapter]:
    """Look up a registered adapter class by name.

    Raises ``KeyError`` if no adapter is registered under *name*.
    """
    if name not in _registry:
        available = ", ".join(sorted(_registry)) or "(none)"
        raise KeyError(f"Unknown adapter: {name!r}. Available: {available}")
    return _registry[name]


def list_adapters() -> list[str]:
    """Return a sorted list of registered adapter names."""
    return sorted(_registry)
