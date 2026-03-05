"""Header file parsing utilities.

Supports simple key-value header file format.
"""

from pathlib import Path


def load_headers_from_file(header_file: str) -> dict[str, str]:
    """Load HTTP headers from file.

    File format is simple ``key: value`` pairs, one per line.
    Lines starting with ``#`` are comments.
    """
    headers: dict[str, str] = {}
    header_path = Path(header_file)

    if not header_path.exists():
        return headers

    with open(header_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip()] = value.strip()

    return headers
