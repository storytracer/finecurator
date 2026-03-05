"""Download manager with concurrent file-level downloads (async-only).

File-level resumability: files are skipped if they already exist.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx
from pydantic import BaseModel
from tqdm import tqdm

from finecurator.http.client import HttpConfig, create_client, download_file

logger = logging.getLogger(__name__)


class DownloadTask(BaseModel):
    """A single download task with URL and destination."""

    url: str
    save_path: Path
    headers: dict[str, str] | None = None
    fallback_url: str | None = None


class DownloadManager:
    """Manages concurrent file downloads with progress tracking.

    Features:
    - File-level resumability (skip existing files)
    - Concurrent downloads via asyncio.Semaphore
    - Progress tracking with tqdm
    - Fallback URL support
    """

    def __init__(
        self,
        config: HttpConfig,
        max_workers: int | None = None,
        show_progress: bool | None = None,
    ):
        self.config = config
        self.max_workers = max_workers or config.max_concurrent
        self.show_progress = show_progress if show_progress is not None else config.show_progress
        self.tasks: list[DownloadTask] = []

    def add_task(self, task: DownloadTask):
        self.tasks.append(task)

    def add_tasks(self, tasks: list[DownloadTask]):
        self.tasks.extend(tasks)

    async def execute(self) -> int:
        """Execute all queued download tasks concurrently.

        Returns:
            Number of successfully downloaded files.
        """
        if not self.tasks:
            logger.warning("No tasks to execute")
            return 0

        successful = 0
        failed = 0
        client = create_client(self.config)

        pbar = None
        if self.show_progress:
            pbar = tqdm(total=len(self.tasks), desc="Downloading", unit="file")

        try:
            semaphore = asyncio.Semaphore(self.max_workers)

            async def _download_with_semaphore(task: DownloadTask):
                async with semaphore:
                    return await self._download_single(client, task)

            coros = [_download_with_semaphore(t) for t in self.tasks]

            for coro in asyncio.as_completed(coros):
                try:
                    success = await coro
                    if success:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Task failed with exception: {e}")
                    failed += 1

                if pbar:
                    pbar.update(1)
                    pbar.set_postfix({"ok": successful, "fail": failed})
        finally:
            await client.aclose()
            if pbar:
                pbar.close()

        self.tasks = []
        logger.info(f"Download complete: {successful} successful, {failed} failed")
        return successful

    async def _download_single(
        self, client: httpx.AsyncClient, task: DownloadTask
    ) -> bool:
        try:
            await download_file(
                client=client,
                url=task.url,
                dest_path=task.save_path,
                config=self.config,
                headers=task.headers,
            )

            if self.config.sleep_interval > 0:
                await asyncio.sleep(self.config.sleep_interval)

            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404 and task.fallback_url:
                logger.warning(f"Primary 404, trying fallback: {task.fallback_url}")
                try:
                    await download_file(
                        client=client,
                        url=task.fallback_url,
                        dest_path=task.save_path,
                        config=self.config,
                        headers=task.headers,
                    )
                    if self.config.sleep_interval > 0:
                        await asyncio.sleep(self.config.sleep_interval)
                    return True
                except Exception as fallback_err:
                    logger.error(f"Fallback failed: {fallback_err}")
                    return False
            else:
                logger.error(f"Failed to download {task.url}: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to download {task.url}: {e}")
            return False

    def clear(self):
        self.tasks = []

    def __len__(self):
        return len(self.tasks)
