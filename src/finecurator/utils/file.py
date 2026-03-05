"""File operation utilities."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_extension(url_or_path: str, default: str = ".jpg") -> str:
    """Extract file extension from URL or path."""
    parsed = urlparse(url_or_path)
    path = Path(parsed.path)
    return path.suffix.lower() if path.suffix else default


def generate_filename(
    index: int,
    extension: str = ".jpg",
    width: int = 4,
    prefix: str = "",
) -> str:
    """Generate a zero-padded filename."""
    number = str(index).zfill(width)
    return f"{prefix}{number}{extension}"
