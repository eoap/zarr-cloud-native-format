from pathlib import Path

import click

from stac_eopf_product.writer import run_to_eopf


@click.command()
@click.option(
    "--stac-catalog",
    type=click.Path(
        path_type=Path,
        exists=True,
        readable=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    help="STAC Catalog file",
    required=True,
)
@click.option(
    "--resolution",
    type=float,
    default=None,
    help="Target output spatial resolution (same unit as target CRS).",
)
@click.option(
    "--chunks",
    type=click.Choice(("manual", "auto"), case_sensitive=False),
    default="manual",
    show_default=True,
    help="Chunking mode. Use 'auto' to let loader decide chunk sizes.",
)
@click.option(
    "--chunk-x",
    type=click.IntRange(min=1),
    default=512,
    show_default=True,
    help="Chunk size along x dimension when --chunks=manual.",
)
@click.option(
    "--chunk-y",
    type=click.IntRange(min=1),
    default=512,
    show_default=True,
    help="Chunk size along y dimension when --chunks=manual.",
)
@click.option(
    "--chunk-time",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Chunk size along time dimension when --chunks=manual.",
)
def to_eopf(
    stac_catalog: Path,
    resolution: float | None,
    chunks: str,
    chunk_x: int,
    chunk_y: int,
    chunk_time: int,
) -> None:
    run_to_eopf(
        stac_catalog=stac_catalog,
        resolution=resolution,
        chunks=chunks.lower(),
        chunk_x=chunk_x,
        chunk_y=chunk_y,
        chunk_time=chunk_time,
    )
