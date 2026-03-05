"""e-rara.ch repo with IIIF, METS metadata, and OCR support.

Combines IIIF images with METS structural metadata and ALTO/plain text OCR.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from finecurator.formats.alto import ALTOParser
from finecurator.formats.iiif import IIIFParser
from finecurator.formats.mets import METSParser
from finecurator.http.client import HttpConfig, create_client
from finecurator.http.download import DownloadManager, DownloadTask
from finecurator.models import CreativeWork, MediaObject, PipelineStage, Record
from finecurator.protocols.iiif import build_iiif_image_url
from finecurator.repos.base import BaseRepo

logger = logging.getLogger(__name__)

_ERARA_ID_PATTERNS = [
    r"/titleinfo/(\d+)",
    r"/v20/(\d+)",
    r"identifier=(\d+)",
    r"/(\d+)/",
    r"/(\d+)$",
]


class ERaraRepo(BaseRepo):
    """Repo for e-rara.ch digital books."""

    name = "erara"

    def __init__(self, config: HttpConfig | None = None):
        self.config = config or HttpConfig()

    async def discover(self, **kwargs: Any) -> AsyncIterator[Record]:
        url = kwargs.get("url")
        if not url:
            raise ValueError("e-rara repo requires a 'url' keyword argument")

        book_id = self._extract_id(url)
        if not book_id:
            raise ValueError(f"Could not extract e-rara book ID from: {url}")

        iiif_url = f"https://www.e-rara.ch/i3f/v20/{book_id}/manifest"
        mets_url = (
            f"https://www.e-rara.ch/oai"
            f"?verb=GetRecord&metadataPrefix=mets&identifier={book_id}"
        )

        client = create_client(self.config)
        try:
            iiif_resp = await client.get(iiif_url)
            iiif_resp.raise_for_status()
            iiif_data = iiif_resp.json()

            mets_resp = await client.get(mets_url)
            mets_resp.raise_for_status()
            mets_data = mets_resp.text
        finally:
            await client.aclose()

        iiif_manifest = IIIFParser().parse(iiif_data)
        mets_doc = METSParser().parse(mets_data)

        work = self._build_work(book_id, url, iiif_manifest, mets_doc)

        yield Record(
            id=book_id,
            source=url,
            stage=PipelineStage.DISCOVERED,
            work=work,
        )

    async def download(self, record: Record, output_dir: Path) -> Record:
        if record.work is None:
            record.errors.append("No work to download")
            return record

        work = record.work
        tasks: list[DownloadTask] = []

        for media in work.all_media:
            if media.role in ("manifest", "structural"):
                continue

            if media.content_url:
                save_dir = output_dir / _role_subdir(media.role)
                save_dir.mkdir(parents=True, exist_ok=True)

                owner = _find_media_owner(work, media)
                if owner and owner.position is not None:
                    pos_str = str(owner.position).zfill(4)
                    ext = _role_extension(media.role)
                    filename = f"{pos_str}{ext}"
                else:
                    filename = media.content_url.split("/")[-1] or "file"

                save_path = save_dir / filename
                media.local_path = save_path

                tasks.append(
                    DownloadTask(
                        url=media.content_url,
                        save_path=save_path,
                        fallback_url=media.fallback_url,
                    )
                )

        if tasks:
            dm = DownloadManager(self.config)
            dm.add_tasks(tasks)
            count = await dm.execute()
            logger.info(f"Downloaded {count} resources for {record.id}")

        work.local_dir = output_dir
        record.stage = PipelineStage.DOWNLOADED
        return record

    async def process(self, record: Record, output_dir: Path) -> Record:
        if record.work is None:
            record.stage = PipelineStage.PROCESSED
            return record

        alto_parser = ALTOParser()
        for page in record.work.get_parts_by_type("CreativeWork"):
            for media in page.get_media_by_role("ocr"):
                if media.local_path and media.local_path.exists():
                    try:
                        alto_xml = media.local_path.read_text(encoding="utf-8")
                        page.text = alto_parser.extract_text_only(alto_xml)
                    except Exception as e:
                        record.errors.append(f"ALTO parse error page {page.position}: {e}")

        record.stage = PipelineStage.PROCESSED
        return record

    def _extract_id(self, url: str) -> str | None:
        for pattern in _ERARA_ID_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _build_work(self, book_id, url, iiif_manifest, mets_doc):
        """Build a CreativeWork tree from IIIF manifest + METS document."""
        mets_md = mets_doc.metadata

        work = CreativeWork(
            id=book_id,
            type="Book",
            name=mets_md.title or f"Book {book_id}",
            url=url,
            creator=mets_md.author or "Unknown",
            date_published=mets_md.date or "Unknown",
            publisher=mets_md.publisher,
            identifier=mets_md.doi,
            in_language=mets_md.language,
            license=mets_md.license,
            description=mets_md.subtitle,
            associated_media=[
                MediaObject(
                    content_url=f"https://www.e-rara.ch/i3f/v20/{book_id}/manifest",
                    role="manifest",
                    encoding_format="application/json",
                ),
                MediaObject(
                    content_url=f"https://www.e-rara.ch/oai?verb=GetRecord&metadataPrefix=mets&identifier={book_id}",
                    role="structural",
                    encoding_format="application/xml",
                ),
            ],
        )

        canvases = iiif_manifest.canvases
        mets_pages = {p.order: p for p in mets_doc.pages}

        for idx, canvas in enumerate(canvases, start=1):
            page_media: list[MediaObject] = []

            for image in canvas.images:
                primary, fallback = build_iiif_image_url(image, self.config)
                page_media.append(
                    MediaObject(
                        content_url=primary,
                        role="image",
                        encoding_format=f"image/{self.config.iiif_format}",
                        fallback_url=fallback,
                        width=image.width or canvas.width,
                        height=image.height or canvas.height,
                    )
                )

            mets_page = mets_pages.get(idx)
            if mets_page:
                for file_id in mets_page.file_ids:
                    mets_file = mets_doc.files.get(file_id)
                    if mets_file and mets_file.href:
                        if file_id.startswith("ALTO") or (mets_file.use and "FULLTEXT" in mets_file.use.upper()):
                            page_media.append(
                                MediaObject(content_url=mets_file.href, role="ocr", encoding_format="application/xml")
                            )
                            plain_url = mets_file.href.replace("/alto3/", "/plain/")
                            if plain_url != mets_file.href:
                                page_media.append(
                                    MediaObject(content_url=plain_url, role="text", encoding_format="text/plain")
                                )

            page_label = canvas.label or (mets_page.label if mets_page else str(idx))

            page = CreativeWork(
                id=canvas.id,
                type="CreativeWork",
                position=idx,
                name=page_label,
                associated_media=page_media,
            )
            work.add_part(page)

        return work

def _role_subdir(role: str | None) -> str:
    return {
        "image": "images",
        "thumbnail": "images",
        "ocr": "ocr/alto",
        "text": "ocr/text",
        "audio": "audio",
        "video": "video",
    }.get(role or "", "other")


def _role_extension(role: str | None) -> str:
    return {
        "image": ".jpg",
        "thumbnail": ".jpg",
        "ocr": ".xml",
        "text": ".txt",
        "audio": ".mp3",
        "video": ".mp4",
    }.get(role or "", "")


def _find_media_owner(root: CreativeWork, media: MediaObject) -> CreativeWork | None:
    """Find the CreativeWork that directly owns a MediaObject."""
    if media in root.associated_media:
        return root
    for part in root.parts:
        result = _find_media_owner(part, media)
        if result:
            return result
    return None
