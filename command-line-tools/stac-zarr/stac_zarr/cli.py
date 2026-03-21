from pathlib import Path

import click

from stac_zarr.constants import OVERVIEW_REDUCERS
from stac_zarr.writer import run_to_zarr


@click.command(
    short_help="Creates a zarr from a STAC catalog",
    help="Creates a zarr from STAC catalog with the water bodies",
)
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
    "--overview-levels",
    type=click.IntRange(min=0),
    default=2,
    show_default=True,
    help="Number of multiscale overview levels to generate.",
)
@click.option(
    "--continuous-overview-reducer",
    type=click.Choice(OVERVIEW_REDUCERS, case_sensitive=False),
    default="mean",
    show_default=True,
    help="Reducer used for continuous variables when generating overviews.",
)
@click.option(
    "--categorical-overview-reducer",
    type=click.Choice(OVERVIEW_REDUCERS, case_sensitive=False),
    default="nearest",
    show_default=True,
    help="Reducer used for categorical variables when generating overviews.",
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
@click.option(
    "--consolidate/--no-consolidate",
    default=True,
    show_default=True,
    help="Write consolidated Zarr metadata after data generation.",
)
@click.option(
    "--titiler-eopf-compatible",
    is_flag=True,
    default=False,
    show_default=True,
    help=(
        "Deprecated compatibility flag. GeoZarr v1 root metadata is always emitted."
    ),
)
@click.option(
    "--stac-object-type",
    type=click.Choice(("collection", "item"), case_sensitive=False),
    default="collection",
    show_default=True,
    help="STAC object type to emit for the Zarr output metadata.",
)
def to_zarr(
    stac_catalog: Path,
    overview_levels: int,
    continuous_overview_reducer: str,
    categorical_overview_reducer: str,
    resolution: float | None,
    chunks: str,
    chunk_x: int,
    chunk_y: int,
    chunk_time: int,
    consolidate: bool,
    titiler_eopf_compatible: bool,
    stac_object_type: str,
) -> None:
    run_to_zarr(
        stac_catalog=stac_catalog,
        overview_levels=overview_levels,
        continuous_overview_reducer=continuous_overview_reducer,
        categorical_overview_reducer=categorical_overview_reducer,
        resolution=resolution,
        chunks=chunks.lower(),
        chunk_x=chunk_x,
        chunk_y=chunk_y,
        chunk_time=chunk_time,
        consolidate=consolidate,
        titiler_eopf_compatible=titiler_eopf_compatible,
        stac_object_type=stac_object_type.lower(),
    )
