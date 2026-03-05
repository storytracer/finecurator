"""IIIF protocol client.

Fetches IIIF manifests, parses them with IIIFParser, and converts the
format-specific models into CreativeWork trees with MediaObject files.
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
from finecurator.models import CreativeWork, MediaObject
from finecurator.protocols.base import BaseProtocol

logger = logging.getLogger(__name__)


def build_iiif_image_url(
    image: IIIFImage, config: HttpConfig
) -> tuple[str, str | None]:
    """Build primary and fallback IIIF Image API URLs for an image resource."""
    if not image.service:
        return (image.id, None)

    service = image.service
    service_id = service.id.rstrip("/")

    api_version = 2
    if service.type and "ImageService3" in service.type:
        api_version = 3
    elif service.context and "/image/3/" in service.context:
        api_version = 3
    elif service.profile and "/image/3/" in str(service.profile):
        api_version = 3

    size_param = "max" if api_version == 3 else "full"

    primary = (
        f"{service_id}/"
        f"{config.iiif_region}/"
        f"{size_param}/"
        f"{config.iiif_rotation}/"
        f"{config.iiif_quality}.{config.iiif_format}"
    )
    fallback = image.id if image.id else None
    return (primary, fallback)


class IIIFClient(BaseProtocol):
    """Protocol client for IIIF Presentation API manifests."""

    def __init__(self, config: HttpConfig | None = None):
        self.config = config or HttpConfig()
        self._parser = IIIFParser()

    async def discover(self, url: str) -> AsyncIterator[CreativeWork]:
        """Fetch a IIIF manifest and yield a CreativeWork tree.

        Each canvas becomes a part with role "image" MediaObjects.
        A "manifest" MediaObject is added at the top level.
        """
        client = create_client(self.config)
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        finally:
            await client.aclose()

        manifest = self._parser.parse(data)
        work = self._manifest_to_work(manifest, url)
        yield work

    async def download_resources(self, work: CreativeWork, output_dir: Path) -> int:
        """Download all media in the CreativeWork tree."""
        tasks: list[DownloadTask] = []
        self._collect_download_tasks(work, output_dir, tasks)

        if not tasks:
            return 0

        dm = DownloadManager(self.config)
        dm.add_tasks(tasks)
        return await dm.execute()

    def _manifest_to_work(
        self,
        manifest: IIIFManifestV2 | IIIFManifestV3,
        manifest_url: str,
    ) -> CreativeWork:
        """Convert parsed IIIF manifest to CreativeWork tree."""
        title = self._extract_title(manifest)

        work = CreativeWork(
            id=manifest.id,
            type="Book",
            name=title,
            url=manifest_url,
            associated_media=[
                MediaObject(content_url=manifest_url, role="manifest", encoding_format="application/json")
            ],
        )

        for idx, canvas in enumerate(manifest.canvases, start=1):
            page = self._canvas_to_work(canvas, idx)
            work.add_part(page)

        return work

    def _canvas_to_work(self, canvas: IIIFCanvas, position: int) -> CreativeWork:
        """Convert a single IIIF canvas to a CreativeWork part."""
        media: list[MediaObject] = []

        for image in canvas.images:
            url, fallback = build_iiif_image_url(image, self.config)
            media.append(
                MediaObject(
                    content_url=url,
                    role="image",
                    encoding_format=f"image/{self.config.iiif_format}",
                    fallback_url=fallback,
                    width=image.width or canvas.width,
                    height=image.height or canvas.height,
                )
            )

        return CreativeWork(
            id=canvas.id,
            type="CreativeWork",
            position=position,
            name=canvas.label or str(position),
            associated_media=media,
        )

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
        work: CreativeWork,
        output_dir: Path,
        tasks: list[DownloadTask],
    ) -> None:
        """Recursively collect download tasks from the CreativeWork tree."""
        if work.position is not None:
            images_dir = output_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            for media in work.associated_media:
                if media.role == "image":
                    filename = f"{str(work.position).zfill(4)}{self.config.file_ext}"
                    save_path = images_dir / filename
                    media.local_path = save_path
                    tasks.append(
                        DownloadTask(
                            url=media.content_url,
                            save_path=save_path,
                            fallback_url=media.fallback_url,
                        )
                    )

        for part in work.parts:
            self._collect_download_tasks(part, output_dir, tasks)
