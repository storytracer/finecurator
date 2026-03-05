"""e-rara.ch adapter with IIIF, METS metadata, and OCR support.

Combines IIIF images with METS structural metadata and ALTO/plain text OCR.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from finecurator.adapters.base import BaseAdapter
from finecurator.formats.alto import ALTOParser
from finecurator.formats.iiif import IIIFParser
from finecurator.formats.mets import METSParser
from finecurator.formats.rocrate import ROCrateWriter
from finecurator.http.client import HttpConfig, create_client
from finecurator.http.download import DownloadManager, DownloadTask
from finecurator.models import (
    Item,
    Metadata,
    PipelineStage,
    Provider,
    ProviderRole,
    Record,
    Resource,
    ResourceRole,
    WorkType,
)

logger = logging.getLogger(__name__)

_ERARA_ID_PATTERNS = [
    r"/titleinfo/(\d+)",
    r"/v20/(\d+)",
    r"identifier=(\d+)",
    r"/(\d+)/",
    r"/(\d+)$",
]


class ERaraAdapter(BaseAdapter):
    """Adapter for e-rara.ch digital books."""

    name = "erara"

    def __init__(self, config: HttpConfig | None = None):
        self.config = config or HttpConfig()

    async def discover(self, **kwargs: Any) -> AsyncIterator[Record]:
        url = kwargs.get("url")
        if not url:
            raise ValueError("e-rara adapter requires a 'url' keyword argument")

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

        item = self._build_item(book_id, url, iiif_manifest, mets_doc, iiif_data, mets_data)

        yield Record(
            id=book_id,
            source=url,
            stage=PipelineStage.DISCOVERED,
            item=item,
        )

    async def download(self, record: Record, output_dir: Path) -> Record:
        if record.item is None:
            record.errors.append("No item to download")
            return record

        item = record.item
        tasks: list[DownloadTask] = []

        # Collect all downloadable resources
        for resource in item.all_resources:
            if resource.role in (ResourceRole.MANIFEST, ResourceRole.STRUCTURAL):
                # Already saved as metadata
                continue

            if resource.url:
                save_dir = output_dir / _role_subdir(resource.role)
                save_dir.mkdir(parents=True, exist_ok=True)

                # Find the page item to get position
                page_item = _find_resource_owner(item, resource)
                if page_item and page_item.position is not None:
                    pos_str = str(page_item.position).zfill(4)
                    ext = _role_extension(resource.role)
                    filename = f"{pos_str}{ext}"
                else:
                    filename = resource.url.split("/")[-1] or "file"

                save_path = save_dir / filename
                resource.local_path = save_path

                tasks.append(
                    DownloadTask(
                        url=resource.url,
                        save_path=save_path,
                        fallback_url=resource.fallback_url,
                    )
                )

        if tasks:
            dm = DownloadManager(self.config)
            dm.add_tasks(tasks)
            count = await dm.execute()
            logger.info(f"Downloaded {count} resources for {record.id}")

        item.local_dir = output_dir
        record.stage = PipelineStage.DOWNLOADED
        return record

    async def process(self, record: Record, output_dir: Path) -> Record:
        if record.item is None:
            record.stage = PipelineStage.PROCESSED
            return record

        alto_parser = ALTOParser()
        for page in record.item.get_children_by_type(WorkType.PAGE):
            for resource in page.get_resources_by_role(ResourceRole.OCR):
                if resource.local_path and resource.local_path.exists():
                    try:
                        alto_xml = resource.local_path.read_text(encoding="utf-8")
                        page.text = alto_parser.extract_text_only(alto_xml)
                    except Exception as e:
                        record.errors.append(f"ALTO parse error page {page.position}: {e}")

        # Write RO-Crate metadata
        try:
            writer = ROCrateWriter()
            writer.write(record.item, output_dir)
        except Exception as e:
            record.errors.append(f"RO-Crate write error: {e}")

        record.stage = PipelineStage.PROCESSED
        return record

    async def extract_metadata(self, record: Record) -> Record:
        return record

    def _extract_id(self, url: str) -> str | None:
        for pattern in _ERARA_ID_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _build_item(self, book_id, url, iiif_manifest, mets_doc, iiif_data, mets_data):
        """Build an Item tree from IIIF manifest + METS document."""
        mets_md = mets_doc.metadata

        metadata = Metadata(
            title=mets_md.title or f"Book {book_id}",
            creator=mets_md.author or "Unknown",
            date=mets_md.date or "Unknown",
            publisher=mets_md.publisher,
            identifier=mets_md.doi,
            language=mets_md.language,
            rights=mets_md.license,
            description=mets_md.subtitle,
            source_url=url,
        )

        doc = Item(
            item_id=book_id,
            work_type=WorkType.DOCUMENT,
            source_url=url,
            metadata=metadata,
            data_provider=Provider(
                name="ETH-Bibliothek", url="https://www.e-rara.ch", role=ProviderRole.DATA_PROVIDER
            ),
            resources=[
                Resource(url=f"https://www.e-rara.ch/i3f/v20/{book_id}/manifest", role=ResourceRole.MANIFEST, mime_type="application/json"),
                Resource(url=f"https://www.e-rara.ch/oai?verb=GetRecord&metadataPrefix=mets&identifier={book_id}", role=ResourceRole.STRUCTURAL, mime_type="application/xml"),
            ],
        )

        # Build page children combining IIIF canvases and METS page info
        canvases = iiif_manifest.canvases
        mets_pages = {p.order: p for p in mets_doc.pages}

        for idx, canvas in enumerate(canvases, start=1):
            page_resources: list[Resource] = []

            # Image from IIIF
            for image in canvas.images:
                primary, fallback = self._build_image_urls(image)
                page_resources.append(
                    Resource(
                        url=primary,
                        role=ResourceRole.IMAGE,
                        mime_type=f"image/{self.config.iiif_format}",
                        fallback_url=fallback,
                        width=image.width or canvas.width,
                        height=image.height or canvas.height,
                    )
                )

            # OCR and text from METS
            mets_page = mets_pages.get(idx)
            if mets_page:
                for file_id in mets_page.file_ids:
                    mets_file = mets_doc.files.get(file_id)
                    if mets_file and mets_file.href:
                        if file_id.startswith("ALTO") or (mets_file.use and "FULLTEXT" in mets_file.use.upper()):
                            page_resources.append(
                                Resource(url=mets_file.href, role=ResourceRole.OCR, mime_type="application/xml")
                            )
                            # Derive plain text URL
                            plain_url = mets_file.href.replace("/alto3/", "/plain/")
                            if plain_url != mets_file.href:
                                page_resources.append(
                                    Resource(url=plain_url, role=ResourceRole.TEXT, mime_type="text/plain")
                                )

            page_label = canvas.label or (mets_page.label if mets_page else str(idx))

            page_item = Item(
                item_id=canvas.id,
                work_type=WorkType.PAGE,
                position=idx,
                label=page_label,
                resources=page_resources,
            )
            doc.add_child(page_item)

        return doc

    def _build_image_urls(self, image) -> tuple[str, str | None]:
        if not image.service:
            return (image.id, None)

        service_id = image.service.id.rstrip("/")

        # Detect API version for size parameter
        api_version = 2
        if image.service.type and "ImageService3" in image.service.type:
            api_version = 3
        elif image.service.context and "/image/3/" in image.service.context:
            api_version = 3

        size_param = "max" if api_version == 3 else "full"

        primary = (
            f"{service_id}/"
            f"{self.config.iiif_region}/"
            f"{size_param}/"
            f"{self.config.iiif_rotation}/"
            f"{self.config.iiif_quality}.{self.config.iiif_format}"
        )
        return (primary, image.id if image.id else None)


def _role_subdir(role: ResourceRole) -> str:
    return {
        ResourceRole.IMAGE: "images",
        ResourceRole.THUMBNAIL: "images",
        ResourceRole.OCR: "ocr/alto",
        ResourceRole.TEXT: "ocr/text",
        ResourceRole.AUDIO: "audio",
        ResourceRole.VIDEO: "video",
    }.get(role, "other")


def _role_extension(role: ResourceRole) -> str:
    return {
        ResourceRole.IMAGE: ".jpg",
        ResourceRole.THUMBNAIL: ".jpg",
        ResourceRole.OCR: ".xml",
        ResourceRole.TEXT: ".txt",
        ResourceRole.AUDIO: ".mp3",
        ResourceRole.VIDEO: ".mp4",
    }.get(role, "")


def _find_resource_owner(root: Item, resource: Resource) -> Item | None:
    """Find the Item that directly owns a resource."""
    if resource in root.resources:
        return root
    for child in root.children:
        result = _find_resource_owner(child, resource)
        if result:
            return result
    return None
