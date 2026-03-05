"""HTTP client utilities using httpx directly (async-only).

Provides helper functions for creating async httpx clients with
proper configuration. Retry logic is handled by tenacity decorators.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from fake_useragent import UserAgent
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from finecurator.http.cookies import load_cookies_from_file
from finecurator.http.headers import load_headers_from_file

logger = logging.getLogger(__name__)


@dataclass
class HttpConfig:
    """Configuration for HTTP client and download behaviour."""

    timeout: int = 300
    use_fake_user_agent: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    proxy: str | None = None
    verify_ssl: bool = False
    cookie_file: str | None = None
    header_file: str | None = None

    max_retries: int = 3
    retry_multiplier: float = 2.0
    retry_wait_min: float = 1.0
    retry_wait_max: float = 10.0

    max_concurrent: int = 16
    sleep_interval: float = 0
    show_progress: bool = True

    iiif_quality: str = "default"
    iiif_format: str = "jpg"
    iiif_region: str = "full"
    iiif_rotation: str = "0"
    file_ext: str = ".jpg"


def create_client(config: HttpConfig) -> httpx.AsyncClient:
    """Create an async httpx client from configuration."""
    if config.use_fake_user_agent:
        ua = UserAgent()
        user_agent = ua.random
    else:
        user_agent = config.user_agent

    headers = {"User-Agent": user_agent}

    if config.header_file and Path(config.header_file).exists():
        file_headers = load_headers_from_file(config.header_file)
        headers.update(file_headers)

    cookies: dict[str, str] = {}
    if config.cookie_file and Path(config.cookie_file).exists():
        cookie_list = load_cookies_from_file(config.cookie_file)
        for cookie in cookie_list:
            cookies[cookie.name] = cookie.value

    return httpx.AsyncClient(
        headers=headers,
        cookies=cookies,
        timeout=config.timeout,
        verify=config.verify_ssl,
        follow_redirects=True,
        http2=True,
        proxy=config.proxy,
        limits=httpx.Limits(max_keepalive_connections=0),
    )


def create_retry_decorator(config: HttpConfig):
    """Create a tenacity retry decorator from config."""
    return retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(
            multiplier=config.retry_multiplier,
            min=config.retry_wait_min,
            max=config.retry_wait_max,
        ),
        retry=retry_if_exception_type(
            (httpx.HTTPError, httpx.TimeoutException, httpx.NetworkError)
        ),
        reraise=True,
    )


async def download_file(
    client: httpx.AsyncClient,
    url: str,
    dest_path: Path,
    config: HttpConfig,
    headers: dict[str, str] | None = None,
) -> Path:
    """Download a file with tenacity retry logic.

    File is only written to disk after complete download.
    If file exists, it is skipped (file-level resumability).
    """
    if dest_path.exists():
        return dest_path

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    retry_decorator = create_retry_decorator(config)

    @retry_decorator
    async def _download_with_retry():
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.content

    content = await _download_with_retry()
    dest_path.write_bytes(content)
    return dest_path
