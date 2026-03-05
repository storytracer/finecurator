"""Format-specific processing: OCR, HTR, image conversion, audio, etc."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def run_ocr(
    image_path: Path,
    *,
    engine: str = "tesseract",
    language: str = "eng",
) -> str:
    """Run OCR on an image file and return extracted text."""
    raise NotImplementedError


def run_htr(image_path: Path, *, model: str = "default") -> str:
    """Run handwritten text recognition on an image."""
    raise NotImplementedError


def convert_image(
    input_path: Path,
    output_path: Path,
    *,
    target_format: str = "png",
    max_dimension: int | None = None,
) -> Path:
    """Convert an image between formats and/or resize."""
    raise NotImplementedError


def process_audio(
    input_path: Path,
    output_path: Path,
    **kwargs: Any,
) -> Path:
    """Process an audio file (transcode, normalize, etc.)."""
    raise NotImplementedError
