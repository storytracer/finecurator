"""Quality validation utilities."""

from __future__ import annotations

from pathlib import Path

from finecurator.models import Record


def validate_text_quality(
    text: str,
    *,
    min_length: int = 0,
    max_error_rate: float = 1.0,
) -> list[str]:
    """Validate text content quality. Returns a list of issues found."""
    raise NotImplementedError


def validate_image_quality(
    image_path: Path,
    *,
    min_resolution: tuple[int, int] = (0, 0),
) -> list[str]:
    """Validate image quality. Returns a list of issues found."""
    raise NotImplementedError


def validate_record_completeness(
    record: Record,
    *,
    required_fields: list[str] | None = None,
) -> list[str]:
    """Check that a record has all required fields populated."""
    raise NotImplementedError
