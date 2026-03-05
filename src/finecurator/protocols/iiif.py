"""IIIF protocol client.

Fetches IIIF manifests, parses them with IIIFParser, and converts the
format-specific models into Item trees with Resource objects.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from pathlib import Path

import httpx

from finecurator.formats.iiif import (
    IIIFCanvas,
    IIIFImage,
    IIIFManifestV2,
    IIIFManifestV3,
    IIIFParser,
)
from finecurator.http.client import HttpConfig, create_client
from finecurator.http.download import DownloadManager, DownloadTask
from finecurator.models import Item, Metadata, Resource, ResourceRole, WorkType
from finecurator.protocols.base import BaseProtocol

logger = logging.getLogger(__name__)


class IIIFClient(BaseProtocol):
    """Protocol client for IIIF Presentation API manifests."""

    def __init__(self, config: HttpConfig | None = None):
        self.config = config or HttpConfig()
        self._parser = IIIFParser()

    async def discover(self, url: str) -> AsyncIterator[Item]:
        """Fetch a IIIF manifest and yield an Item(DOCUMENT) tree.

        Each canvas becomes an Item(PAGE) child with Resource(IMAGE).
        A Resource(MANIFEST) is added at document level.
        """
        client = create_client(self.config)
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        finally:
            await client.aclose()

        manifest = self._parser.parse(data)
        item = self._manifest_to_item(manifest, url)
        yield item

    async def download_resources(self, item: Item, output_dir: Path) -> int:
        """Download all resources in the Item tree."""
        tasks: list[DownloadTask] = []
        self._collect_download_tasks(item, output_dir, tasks)

        if not tasks:
            return 0

        dm = DownloadManager(self.config)
        dm.add_tasks(tasks)
        count = await dm.execute()

        # Update local_path on resources
        for resource in item.all_resources:
            if resource.local_path and resource.local_path.exists():
                continue  # already set

        return count

    def _manifest_to_item(
        self,
        manifest: IIIFManifestV2 | IIIFManifestV3,
        manifest_url: str,
    ) -> Item:
        """Convert parsed IIIF manifest to Item tree."""
        title = self._extract_title(manifest)

        doc = Item(
            item_id=manifest.id,
            work_type=WorkType.DOCUMENT,
            source_url=manifest_url,
            metadata=Metadata(title=title, source_url=manifest_url),
            resources=[
                Resource(url=manifest_url, role=ResourceRole.MANIFEST, mime_type="application/json")
            ],
        )

        canvases = manifest.canvases
        for idx, canvas in enumerate(canvases, start=1):
            page_item = self._canvas_to_item(canvas, idx)
            doc.add_child(page_item)

        return doc

    def _canvas_to_item(self, canvas: IIIFCanvas, position: int) -> Item:
        """Convert a single IIIF canvas to an Item(PAGE)."""
        resources: list[Resource] = []

        for image in canvas.images:
            url, fallback = self._build_image_urls(image)
            resources.append(
                Resource(
                    url=url,
                    role=ResourceRole.IMAGE,
                    mime_type=f"image/{self.config.iiif_format}",
                    fallback_url=fallback,
                    width=image.width or canvas.width,
                    height=image.height or canvas.height,
                )
            )

        return Item(
            item_id=canvas.id,
            work_type=WorkType.PAGE,
            position=position,
            label=canvas.label or str(position),
            resources=resources,
        )

    def _build_image_urls(self, image: IIIFImage) -> tuple[str, str | None]:
        """Build primary and fallback URLs for an IIIF image."""
        if not image.service:
            return (image.id, None)

        service_id = image.service.id.rstrip("/")
        api_version = self._detect_image_api_version(image.service)
        size_param = "max" if api_version == 3 else "full"

        primary = (
            f"{service_id}/"
            f"{self.config.iiif_region}/"
            f"{size_param}/"
            f"{self.config.iiif_rotation}/"
            f"{self.config.iiif_quality}.{self.config.iiif_format}"
        )
        fallback = image.id if image.id else None
        return (primary, fallback)

    def _detect_image_api_version(self, service) -> int:
        if not service:
            return 2
        if service.type and "ImageService3" in service.type:
            return 3
        if service.context and "/image/3/" in service.context:
            return 3
        if service.profile:
            profile_str = str(service.profile)
            if "/image/3/" in profile_str:
                return 3
        return 2

    def _extract_title(self, manifest: IIIFManifestV2 | IIIFManifestV3) -> str:
        if hasattr(manifest, "label"):
            label = manifest.label
            if isinstance(label, dict):
                for vals in label.values():
                    if vals:
                        return vals[0]
            elif isinstance(label, str):
                return label
        return "unknown"

    def _collect_download_tasks(
        self,
        item: Item,
        output_dir: Path,
        tasks: list[DownloadTask],
    ) -> None:
        """Recursively collect download tasks from the Item tree."""
        if item.work_type == WorkType.PAGE and item.position is not None:
            images_dir = output_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            for resource in item.resources:
                if resource.role == ResourceRole.IMAGE:
                    filename = f"{str(item.position).zfill(4)}{self.config.file_ext}"
                    save_path = images_dir / filename
                    resource.local_path = save_path
                    tasks.append(
                        DownloadTask(
                            url=resource.url,
                            save_path=save_path,
                            fallback_url=resource.fallback_url,
                        )
                    )

        for child in item.children:
            self._collect_download_tasks(child, output_dir, tasks)
