# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FineCurator is a modular Python toolkit for downloading, processing, and curating datasets from cultural heritage sources (GLAM sector). It serves as the data pipeline behind FineBooks. It functions both as a library and a CLI tool.

## Commands

```bash
# Install dependencies (requires Python 3.12+, uses uv)
uv sync

# Run CLI
uv run finecurator <command>

# Example CLI commands
uv run finecurator adapters          # List registered adapters
uv run finecurator run <source> -o ./output
uv run finecurator discover <source>
uv run finecurator download <source> -o ./output
uv run finecurator process <source> -o ./output
```

No test suite exists yet. No linter/formatter is configured in pyproject.toml.

## Architecture

The codebase follows a pipeline pattern with three key abstractions:

**Record** (`models.py`) - A dataclass that flows through all pipeline stages, accumulating data: ID, source, stage enum, metadata, local file paths, and errors.

**BaseAdapter** (`adapters/base.py`) - Abstract base class for source-specific logic. Concrete subclasses set a `name` class variable and are **auto-registered** into the global registry via `__init_subclass__`. The adapter must implement: `discover`, `download`, `process`, `extract_metadata`.

**Pipeline** (`pipeline.py`) - Orchestrates six stages as lazy iterators: discover -> download -> process -> clean -> validate -> output. Each stage is independently runnable. Clean, validate, and output stages are currently placeholders.

**Registry** (`registry.py`) - Global dict mapping adapter names to classes. Adapters register themselves automatically; looked up by `get_adapter(name)`.

**BaseStage** (`stages/base.py`) - Abstract base for composable pipeline stages (alternative to adapter-driven stages). Not yet wired into the pipeline.

**Utilities** (`utils/`) - Stub modules for shared functionality: `download.py` (HTTP/IIIF with retry/resume), `processing.py` (OCR, HTR, image/audio conversion), `cleaning.py` (whitespace/unicode normalization, dedup), `metadata.py` (merge, date/language normalization), `validation.py` (text/image quality, record completeness). All raise `NotImplementedError`.

## Key Patterns

- Adapters auto-register: just subclass `BaseAdapter` with a `name` and implement the abstract methods. No manual registration needed.
- Pipeline stages use lazy iterators (`Iterator[Record]`) for memory efficiency.
- The CLI (`cli.py`) uses Click and mirrors the pipeline stages as subcommands.
- Public API is exported from `__init__.py`: `BaseAdapter`, `Pipeline`, `Record`, `Metadata`, `PipelineContext`, `PipelineStage`, `get_adapter`, `list_adapters`.
