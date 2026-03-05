"""HTTP and IIIF download utilities with retry and resume support."""

from __future__ import annotations

from pathlib import Path


def download_file(
    url: str,
    dest: Path,
    *,
    headers: dict[str, str] | None = None,
    retries: int = 3,
    resume: bool = True,
    timeout: float = 30.0,
) -> Path:
    """Download a file from a URL with retry and resume support."""
    raise NotImplementedError


def download_iiif_manifest(
    manifest_url: str,
    dest_dir: Path,
    *,
    max_dimension: int | None = None,
    retries: int = 3,
) -> list[Path]:
    """Download all images referenced by a IIIF manifest."""
    raise NotImplementedError
