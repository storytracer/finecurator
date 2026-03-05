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
# List available source adapters
finecurator adapters

# Run the full pipeline for a IIIF manifest
finecurator run iiif --url https://example.org/manifest.json -o ./output

# Run the full pipeline for an e-rara book
finecurator run erara --url https://www.e-rara.ch/stp/content/titleinfo/24224395 -o ./output

# Run individual stages
finecurator discover iiif --url https://example.org/manifest.json
finecurator download iiif --url https://example.org/manifest.json -o ./output

# Verbose logging
finecurator -v run iiif --url https://example.org/manifest.json -o ./output
```

### Library

```python
import asyncio
from finecurator import Pipeline, Item, WorkType, Resource, ResourceRole

# Run a full pipeline
async def main():
    pipeline = Pipeline(adapter_name="iiif", output_dir="./output")
    async for record in pipeline.run(url="https://example.org/manifest.json"):
        print(record.id, record.stage)
        if record.item:
            print(f"  {record.item.metadata.title}")
            print(f"  {len(record.item.all_resources)} resources")

asyncio.run(main())
```

### Building Item trees

Everything is an `Item` with a `work_type` enum. Items form trees via `children`/`parent`:

```python
from finecurator import Item, Metadata, Resource, ResourceRole, WorkType, Provider, ProviderRole

# A multi-volume encyclopedia
enc = Item(
    item_id="enc-001",
    work_type=WorkType.WORK,
    metadata=Metadata(title="Encyclopedie", creator="Diderot"),
    data_provider=Provider(name="BNF", role=ProviderRole.DATA_PROVIDER),
)

vol1 = Item(item_id="v1", work_type=WorkType.VOLUME, position=1, label="Tome I")
page1 = Item(
    item_id="p1", work_type=WorkType.PAGE, position=1, label="1",
    resources=[Resource(url="https://example.com/p1.jpg", role=ResourceRole.IMAGE)],
)
vol1.add_child(page1)
enc.add_child(vol1)

# Traverse the tree
print(enc.all_descendants)   # [vol1, page1]
print(enc.all_resources)     # [Resource(...)]
print(vol1.parent is enc)    # True
```

## Architecture

### Data Model

A single unified `Item` class with a `work_type` enum replaces separate classes for documents, images, audio, etc. This allows mixed-type hierarchies (e.g. a newspaper issue containing both articles and images) without class hierarchy gymnastics.

- **`Item`** -- the universal node. Has `item_id`, `work_type` (WorkType enum), `position` (machine-readable order), `label` (human display string), `metadata` (Dublin Core), `text` (inline text content), `resources` (attached files), `children`/`parent` (tree), and provider fields.
- **`Resource`** -- a downloadable file with `url`, `role` (ResourceRole enum), `mime_type`, `local_path`, `fallback_url`, and dimensions.
- **`Provider`** -- data provenance with `name`, `url`, and `role` (DATA_PROVIDER, INTERMEDIATE, AGGREGATOR).
- **`Record`** -- pipeline envelope wrapping an `Item` with `stage`, `source`, and `errors`.

### Adapters

Source adapters encapsulate all source-specific logic behind an async interface: `discover`, `download`, `process`, `extract_metadata`. Concrete adapters subclass `BaseAdapter` and are automatically registered by name.

Built-in adapters:
- **`iiif`** -- generic adapter for any IIIF Presentation API manifest (v2/v3)
- **`erara`** -- e-rara.ch adapter combining IIIF images + METS metadata + ALTO OCR

### HTTP

Async HTTP client built on `httpx` with HTTP/2 support, `tenacity` retry with exponential backoff, fake user agents, cookie/header file support, and a concurrent `DownloadManager` with tqdm progress bars.

### Formats

Pure parsers producing format-specific dataclasses (no I/O):
- **IIIF** -- parses Presentation API v2/v3 manifests
- **METS** -- parses METS XML with MODS metadata extraction
- **ALTO** -- parses ALTO XML v1-4 for OCR text
- **RO-Crate** -- writes RO-Crate metadata from Item trees (Dublin Core to Schema.org mapping)

### Protocols

Convert format models to `Item` trees:
- **IIIFClient** -- fetches manifests, creates `Item(DOCUMENT)` with `Item(PAGE)` children
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

## Adding an adapter

Create a subclass of `BaseAdapter` with a `name` class variable:

```python
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from finecurator import BaseAdapter, Record

class MySourceAdapter(BaseAdapter):
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

The adapter is automatically registered and available via `finecurator run my-source` and `get_adapter("my-source")`.

## Dependencies

- [httpx](https://www.python-httpx.org/) (HTTP/2 client)
- [tenacity](https://tenacity.readthedocs.io/) (retry logic)
- [tqdm](https://tqdm.github.io/) (progress bars)
- [fake-useragent](https://github.com/fake-useragent/fake-useragent) (request masking)
- [rocrate](https://github.com/ResearchObject/ro-crate-py) (RO-Crate metadata)
- [tldextract](https://github.com/john-googler/tldextract) (domain parsing)
- [url64](https://github.com/nicois/url64) (URL-safe base64 slugs)
- [click](https://click.palletsprojects.com/) (CLI framework)
