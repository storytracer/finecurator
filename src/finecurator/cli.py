"""Command-line interface for FineCurator."""

from __future__ import annotations

from pathlib import Path

import click

from finecurator.pipeline import Pipeline
from finecurator.registry import get_adapter, list_adapters


@click.group()
def cli() -> None:
    """FineCurator: A toolkit for curating cultural heritage datasets."""


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
def run(source: str, output_dir: Path) -> None:
    """Run the full pipeline for SOURCE."""
    pipeline = Pipeline(adapter_name=source, output_dir=output_dir)
    for record in pipeline.run():
        click.echo(f"[{record.stage.value}] {record.id}")


@cli.command()
@click.argument("source")
def discover(source: str) -> None:
    """Discover records from SOURCE."""
    adapter_cls = get_adapter(source)
    adapter = adapter_cls()
    for record in adapter.discover():
        click.echo(record.id)


@cli.command()
@click.argument("source")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
def download(source: str, output_dir: Path) -> None:
    """Download records from SOURCE."""
    pipeline = Pipeline(adapter_name=source, output_dir=output_dir)
    for record in pipeline.download(pipeline.discover()):
        click.echo(f"[downloaded] {record.id}")


@cli.command()
@click.argument("source")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=Path("output"))
def process(source: str, output_dir: Path) -> None:
    """Process downloaded records from SOURCE."""
    pipeline = Pipeline(adapter_name=source, output_dir=output_dir)
    records = pipeline.download(pipeline.discover())
    for record in pipeline.process(records):
        click.echo(f"[processed] {record.id}")


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
