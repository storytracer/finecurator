# FineCurator

A modular Python toolkit for downloading, processing, and curating datasets from cultural heritage sources. FineCurator is both a library and a CLI tool.

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

# Run the full pipeline for a source
finecurator run <source> --output-dir ./output

# Run individual stages
finecurator discover <source>
finecurator download <source> --output-dir ./output
finecurator process <source> --output-dir ./output
```

### Library

```python
from finecurator import Pipeline, BaseAdapter, get_adapter, list_adapters

# Run a full pipeline
pipeline = Pipeline(adapter_name="source-name", output_dir="./output")
for record in pipeline.run():
    print(record.id, record.stage)

# Run individual stages
for record in pipeline.discover():
    print(record.id)
```

## Architecture

**Source adapters** encapsulate all source-specific logic (API auth, pagination, rate limiting, format quirks) behind a common interface: `discover`, `download`, `process`, `extract_metadata`. Concrete adapters subclass `BaseAdapter` and are automatically registered by name.

**Shared utilities** provide reusable building blocks for downloading (HTTP/IIIF with retries and resume), format processing (OCR, HTR, image conversion, audio), cleaning and normalization, metadata handling, and quality validation. Adapters compose these utilities rather than reimplementing them.

**Pipeline** orchestrates the flow from raw source to curated output through six stages: discover, download, process, clean, validate, output. Each stage is independently runnable and resumable, operating on lazy iterators for memory efficiency.

Everything available through the CLI is equally available as a library import.

## Adding an adapter

Create a subclass of `BaseAdapter` with a `name` class variable:

```python
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from finecurator import BaseAdapter, Record

class MySourceAdapter(BaseAdapter):
    name = "my-source"

    def discover(self, **kwargs: Any) -> Iterator[Record]:
        ...

    def download(self, record: Record, output_dir: Path) -> Record:
        ...

    def process(self, record: Record, output_dir: Path) -> Record:
        ...

    def extract_metadata(self, record: Record) -> Record:
        ...
```

The adapter is automatically registered and available via `finecurator run my-source` and `get_adapter("my-source")`.
