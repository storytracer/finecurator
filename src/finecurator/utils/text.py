"""Text and URL parsing utilities."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import tldextract
import url64


def extract_between(text: str, start: str, end: str) -> str | None:
    """Extract text between two markers."""
    try:
        start_idx = text.index(start) + len(start)
        end_idx = text.index(end, start_idx)
        return text[start_idx:end_idx]
    except ValueError:
        return None


def get_domain(url: str) -> str:
    """Extract root-level domain from URL using tldextract."""
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}"


def get_host_url(url: str) -> str:
    """Extract scheme and host from URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def extract_id_from_url(url: str, pattern: str | None = None) -> str | None:
    """Extract ID from URL using regex pattern or last path segment."""
    if pattern:
        match = re.search(pattern, url)
        return match.group(1) if match else None
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split("/") if p]
    return path_parts[-1] if path_parts else None


def url_to_slug(url: str) -> str:
    """Convert URL to a reversible, filesystem-safe base64url slug."""
    try:
        return url64.encode(url)
    except Exception as e:
        raise ValueError(f"Failed to encode URL to slug: {e}")


def slug_to_url(slug: str) -> str:
    """Decode a base64url slug back to the original URL."""
    try:
        return url64.decode(slug)
    except Exception as e:
        raise ValueError(f"Failed to decode slug to URL: {e}")
