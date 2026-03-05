"""Global repo registry for dynamic lookup by name."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finecurator.repos.base import BaseRepo

_registry: dict[str, type[BaseRepo]] = {}


def register(name: str, repo_cls: type[BaseRepo]) -> None:
    """Register a repo class under the given name."""
    if name in _registry:
        raise ValueError(f"Repo already registered: {name!r}")
    _registry[name] = repo_cls


def get_repo(name: str) -> type[BaseRepo]:
    """Look up a registered repo class by name.

    Raises ``KeyError`` if no repo is registered under *name*.
    """
    if name not in _registry:
        available = ", ".join(sorted(_registry)) or "(none)"
        raise KeyError(f"Unknown repo: {name!r}. Available: {available}")
    return _registry[name]


def list_repos() -> list[str]:
    """Return a sorted list of registered repo names."""
    return sorted(_registry)
