from pathlib import Path

import click

from stac_collection.writer import run_to_stac


@click.command(
    short_help="Creates a STAC catalog",
    help="Creates a STAC catalog with the water bodies",
)
@click.option(
    "--input-item",
    "item_urls",
    help="STAC Item URL",
    required=True,
    multiple=True,
)
@click.option(
    "--otsu",
    "otsu",
    help="otsu mask geotiff",
    required=True,
    multiple=True,
)
@click.option(
    "--ndwi",
    "ndwi",
    help="NDWI geotiff",
    required=True,
    multiple=True,
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path("."),
    show_default=True,
    help="Output directory for the generated STAC catalog and assets.",
)
def to_stac(
    item_urls: tuple[str, ...],
    otsu: tuple[str, ...],
    ndwi: tuple[str, ...],
    output_dir: Path,
) -> None:
    run_to_stac(item_urls=item_urls, otsu=otsu, ndwi=ndwi, output_dir=output_dir)
