# FineCurator

A modular Python toolkit for downloading, processing, and curating datasets from cultural heritage sources. Successor to [pybookget](https://github.com/storytracer/pybookget). FineCurator is both a library and a CLI tool.

FineCurator serves as the data pipeline behind FineBooks, a curated dataset of public domain digitized books. While the initial focus is books, the architecture generalizes to any cultural heritage dataset across the GLAM sector (Galleries, Libraries, Archives, Museums), including digitized text, images, audio, and multimedia collections.

## Installation

Requires Python 3.12+. Install with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

## Usage

### CLI

```bash
# List available source repos
finecurator repos

# Fetch and download a IIIF manifest directly
finecurator iiif https://example.org/manifest.json -o ./output

# Run the full pipeline for an e-rara book
finecurator run erara --url https://www.e-rara.ch/stp/content/titleinfo/24224395 -o ./output

# Run individual stages
finecurator discover erara --url https://www.e-rara.ch/stp/content/titleinfo/24224395
finecurator download erara --url https://www.e-rara.ch/stp/content/titleinfo/24224395 -o ./output

# Verbose logging
finecurator -v run erara --url https://www.e-rara.ch/stp/content/titleinfo/24224395 -o ./output
```

### Library

```python
import asyncio
from finecurator import Pipeline

async def main():
    pipeline = Pipeline(repo_name="erara", output_dir="./output")
    async for record in pipeline.run(url="https://www.e-rara.ch/stp/content/titleinfo/24224395"):
        print(record.id, record.stage)
        if record.work:
            print(f"  {record.work.name}")
            print(f"  {len(record.work.all_media)} media files")

asyncio.run(main())
```

### Building CreativeWork trees

Everything is a `CreativeWork` with a `type` string. Works form trees via `parts`/`is_part_of`. All models are Pydantic `BaseModel` subclasses with full serialization support:

```python
from finecurator import CreativeWork, MediaObject

book = CreativeWork(
    id="book-001",
    type="Book",
    name="Encyclopedie",
    creator="Diderot",
)

page = CreativeWork(
    id="p1",
    type="CreativeWork",
    position=1,
    name="1",
    associated_media=[
        MediaObject(content_url="https://example.com/p1.jpg", role="image"),
    ],
)
book.add_part(page)

# Traverse the tree
print(book.all_parts)   # [page]
print(book.all_media)   # [MediaObject(...)]
print(page.is_part_of is book)  # True

# Serialize to JSON
print(book.model_dump_json(indent=2))

# Deserialize from JSON
book2 = CreativeWork.model_validate_json(book.model_dump_json())
```

## Architecture

### Data Model

Built on Schema.org vocabulary. All models are Pydantic `BaseModel` subclasses.

- **`CreativeWork`** -- the universal node. Has `id`, `type` (str, e.g. "Book", "Collection"), `name`, `url`, `position`, Schema.org properties (`creator`, `date_published`, `in_language`, etc.), `parts`/`is_part_of` (tree hierarchy), `associated_media` (attached files), and `extra` (extension point).
- **`MediaObject`** -- a downloadable file with `content_url`, `role` (str, e.g. "image", "ocr", "text"), `encoding_format`, `local_path`, `fallback_url`, and dimensions.
- **`Record`** -- pipeline envelope wrapping a `CreativeWork` with `stage`, `source`, and `errors`.
- **`PipelineContext`** -- runtime context with `repo_name`, `output_dir`, `state_dir`, `config`.

### Repos

Source repos encapsulate all source-specific logic behind an async interface: `discover`, `download`, `process`, `extract_metadata`. Concrete repos subclass `BaseRepo` and are automatically registered by name.

Built-in repos:
- **`erara`** -- e-rara.ch repo combining IIIF images + METS metadata + ALTO OCR

### HTTP

Async HTTP client built on `httpx` with HTTP/2 support, `tenacity` retry with exponential backoff, fake user agents, cookie/header file support, and a concurrent `DownloadManager` with tqdm progress bars. `HttpConfig` and `DownloadTask` are Pydantic models.

### Formats

Pure parsers producing format-specific Pydantic models (no I/O):
- **IIIF** -- parses Presentation API v2/v3 manifests
- **METS** -- parses METS XML with MODS metadata extraction
- **ALTO** -- parses ALTO XML v1-4 for OCR text

### Protocols

Convert format models to `CreativeWork` trees:
- **IIIFClient** -- fetches manifests, creates `CreativeWork(type="Book")` with page parts
- **OAIPMHClient** -- stub for future OAI-PMH support

### Pipeline

Orchestrates the flow from raw source to curated output through six async stages: discover, download, process, clean, validate, output. Each stage is independently runnable, operating on async iterators for memory efficiency.

### Utilities

- **`utils/text.py`** -- URL parsing, domain extraction, base64url slugs
- **`utils/file.py`** -- file operations, filename generation
- **`utils/processing.py`** -- OCR/HTR/image conversion stubs
- **`utils/cleaning.py`** -- text normalization stubs
- **`utils/metadata.py`** -- metadata merge/normalization stubs
- **`utils/validation.py`** -- quality validation stubs

## Adding a repo

Create a subclass of `BaseRepo` with a `name` class variable:

```python
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from finecurator import BaseRepo, Record

class MySourceRepo(BaseRepo):
    name = "my-source"

    async def discover(self, **kwargs: Any) -> AsyncIterator[Record]:
        ...

    async def download(self, record: Record, output_dir: Path) -> Record:
        ...

    async def process(self, record: Record, output_dir: Path) -> Record:
        ...

    async def extract_metadata(self, record: Record) -> Record:
        ...
```

The repo is automatically registered and available via `finecurator run my-source` and `get_repo("my-source")`.

## Dependencies

- [click](https://click.palletsprojects.com/) (CLI framework)
- [httpx](https://www.python-httpx.org/) (HTTP/2 client)
- [pydantic](https://docs.pydantic.dev/) (data models, serialization)
- [tenacity](https://tenacity.readthedocs.io/) (retry logic)
- [tqdm](https://tqdm.github.io/) (progress bars)
- [fake-useragent](https://github.com/fake-useragent/fake-useragent) (request masking)
- [tldextract](https://github.com/john-googler/tldextract) (domain parsing)
- [url64](https://github.com/nicois/url64) (URL-safe base64 slugs)
