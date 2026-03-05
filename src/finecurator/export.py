"""Export system: convert downloaded files without modifying originals."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image

from finecurator.formats.alto import ALTOParser
from finecurator.models import PipelineStage, Record

logger = logging.getLogger(__name__)

# MIME type → Pillow format string
_PILLOW_FORMATS: dict[str, str] = {
    "png": "PNG",
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "webp": "WEBP",
    "tiff": "TIFF",
    "tif": "TIFF",
    "bmp": "BMP",
}

_FORMAT_EXTENSIONS: dict[str, str] = {
    "png": ".png",
    "jpg": ".jpg",
    "jpeg": ".jpg",
    "webp": ".webp",
    "tiff": ".tif",
    "tif": ".tif",
    "bmp": ".bmp",
    "text": ".txt",
    "txt": ".txt",
}

_IMAGE_MIME_PREFIXES = ("image/jpeg", "image/png", "image/tiff", "image/webp", "image/bmp")


class Exporter(ABC):
    """Base class for export converters."""

    @abstractmethod
    async def export(self, record: Record, output_dir: Path) -> Record:
        """Export/convert a downloaded record.

        Writes converted files to ``output_dir / record.id / export/``.
        Must NOT modify original downloaded files.
        Returns the record updated to EXPORTED stage.
        """
        ...


class ImageExporter(Exporter):
    """Convert images between formats using Pillow."""

    def __init__(self, target_format: str = "png") -> None:
        self.target_format = target_format.lower()
        if self.target_format not in _PILLOW_FORMATS:
            raise ValueError(
                f"Unsupported image format: {target_format}. "
                f"Supported: {', '.join(_PILLOW_FORMATS)}"
            )

    async def export(self, record: Record, output_dir: Path) -> Record:
        if record.work is None:
            record.stage = PipelineStage.EXPORTED
            return record

        export_dir = output_dir / record.id / "export" / "images"
        export_dir.mkdir(parents=True, exist_ok=True)
        pillow_fmt = _PILLOW_FORMATS[self.target_format]
        ext = _FORMAT_EXTENSIONS[self.target_format]
        converted = 0

        for part in record.work.parts:
            for media in part.associated_media:
                if not media.local_path or not media.local_path.exists():
                    continue
                if not (media.encoding_format or "").startswith("image/"):
                    continue

                stem = media.local_path.stem
                out_path = export_dir / f"{stem}{ext}"

                if out_path.exists():
                    converted += 1
                    continue

                try:
                    with Image.open(media.local_path) as img:
                        img.save(out_path, format=pillow_fmt)
                    converted += 1
                except Exception as e:
                    record.errors.append(f"Image export error {media.local_path.name}: {e}")

        logger.info("Exported %d images to %s format for %s", converted, self.target_format, record.id)
        record.stage = PipelineStage.EXPORTED
        return record


class TextExporter(Exporter):
    """Extract plain text from ALTO XML files."""

    async def export(self, record: Record, output_dir: Path) -> Record:
        if record.work is None:
            record.stage = PipelineStage.EXPORTED
            return record

        export_dir = output_dir / record.id / "export" / "text"
        export_dir.mkdir(parents=True, exist_ok=True)
        alto_parser = ALTOParser()
        extracted = 0

        for part in record.work.parts:
            for media in part.associated_media:
                if not media.local_path or not media.local_path.exists():
                    continue
                if media.encoding_format != "application/xml":
                    continue

                stem = media.local_path.stem
                out_path = export_dir / f"{stem}.txt"

                if out_path.exists():
                    extracted += 1
                    continue

                try:
                    alto_xml = media.local_path.read_text(encoding="utf-8")
                    text = alto_parser.extract_text_only(alto_xml)
                    out_path.write_text(text, encoding="utf-8")
                    part.text = text
                    extracted += 1
                except Exception as e:
                    record.errors.append(f"ALTO export error {media.local_path.name}: {e}")

        logger.info("Exported %d text files for %s", extracted, record.id)
        record.stage = PipelineStage.EXPORTED
        return record


def get_exporter(export_format: str) -> Exporter:
    """Get the appropriate exporter for a format string."""
    fmt = export_format.lower()
    if fmt in ("text", "txt"):
        return TextExporter()
    if fmt in _PILLOW_FORMATS:
        return ImageExporter(target_format=fmt)
    raise ValueError(
        f"Unknown export format: {export_format}. "
        f"Supported: {', '.join(sorted(set(list(_PILLOW_FORMATS) + ['text', 'txt'])))}"
    )
