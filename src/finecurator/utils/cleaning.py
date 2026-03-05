"""Cleaning and normalization utilities."""

from __future__ import annotations


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace into single spaces and strip."""
    raise NotImplementedError


def normalize_unicode(text: str, form: str = "NFC") -> str:
    """Normalize Unicode text to the given normal form."""
    raise NotImplementedError


def remove_boilerplate(
    text: str,
    *,
    patterns: list[str] | None = None,
) -> str:
    """Remove common boilerplate text (headers, footers, etc.)."""
    raise NotImplementedError


def deduplicate_records(records: list, *, key: str = "id") -> list:
    """Remove duplicate records based on a key field."""
    raise NotImplementedError
