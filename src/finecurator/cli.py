"""Command-line interface for FineCurator."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import click

# Import adapters so they auto-register
import finecurator.adapters.erara  # noqa: F401
import finecurator.adapters.iiif  # noqa: F401
from finecurator.pipeline import Pipeline
from finecurator.registry import get_adapter, list_adapters


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging.")
def cli(verbose: bool) -> None:
    """FineCurator: A toolkit for curating cultural heritage datasets."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )


@cli.command("adapters")
def list_adapters_cmd() -> None:
    """List available source adapters."""
    names = list_adapters()
    if not names:
        click.echo("No adapters registered.")
        return
    for name in names:
        click.echo(name)


@cli.command()
@click.argument("source")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
@click.option("--url", default=None, help="Source URL (manifest, page, etc.).")
def run(source: str, output_dir: Path, url: str | None) -> None:
    """Run the full pipeline for SOURCE."""
    kwargs = {}
    if url:
        kwargs["url"] = url

    async def _run():
        pipeline = Pipeline(adapter_name=source, output_dir=output_dir)
        async for record in pipeline.run(**kwargs):
            click.echo(f"[{record.stage.value}] {record.id}")
            if record.errors:
                for err in record.errors:
                    click.echo(f"  ERROR: {err}", err=True)

    asyncio.run(_run())


@cli.command()
@click.argument("source")
@click.option("--url", default=None, help="Source URL.")
def discover(source: str, url: str | None) -> None:
    """Discover records from SOURCE."""
    kwargs = {}
    if url:
        kwargs["url"] = url

    async def _discover():
        adapter_cls = get_adapter(source)
        adapter = adapter_cls()
        async for record in adapter.discover(**kwargs):
            title = record.item.metadata.title if record.item else ""
            click.echo(f"{record.id}  {title}")

    asyncio.run(_discover())


@cli.command()
@click.argument("source")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
@click.option("--url", default=None, help="Source URL.")
def download(source: str, output_dir: Path, url: str | None) -> None:
    """Download records from SOURCE."""
    kwargs = {}
    if url:
        kwargs["url"] = url

    async def _download():
        pipeline = Pipeline(adapter_name=source, output_dir=output_dir)
        async for record in pipeline.download(pipeline.discover(**kwargs)):
            click.echo(f"[downloaded] {record.id}")

    asyncio.run(_download())


@cli.command()
@click.argument("source")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
@click.option("--url", default=None, help="Source URL.")
def process(source: str, output_dir: Path, url: str | None) -> None:
    """Process downloaded records from SOURCE."""
    kwargs = {}
    if url:
        kwargs["url"] = url

    async def _process():
        pipeline = Pipeline(adapter_name=source, output_dir=output_dir)
        records = pipeline.download(pipeline.discover(**kwargs))
        async for record in pipeline.process(records):
            click.echo(f"[processed] {record.id}")

    asyncio.run(_process())


@cli.command()
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
def clean(output_dir: Path) -> None:
    """Clean processed records."""
    click.echo("Clean stage: not yet implemented.")


@cli.command()
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
def validate(output_dir: Path) -> None:
    """Validate cleaned records."""
    click.echo("Validate stage: not yet implemented.")


@cli.command()
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
def output(output_dir: Path) -> None:
    """Output curated dataset."""
    click.echo("Output stage: not yet implemented.")
