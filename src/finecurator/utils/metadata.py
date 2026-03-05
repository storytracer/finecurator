"""Metadata extraction and normalization utilities."""

from __future__ import annotations

from finecurator.models import Metadata


def merge_metadata(*sources: Metadata) -> Metadata:
    """Merge multiple Metadata objects, with later values taking precedence."""
    raise NotImplementedError


def normalize_date(raw_date: str) -> str | None:
    """Normalize a date string to ISO 8601 format."""
    raise NotImplementedError


def normalize_language(raw_lang: str) -> str | None:
    """Normalize a language identifier to ISO 639."""
    raise NotImplementedError
