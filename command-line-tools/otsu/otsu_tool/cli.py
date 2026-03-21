import click

from otsu_tool.writer import run_otsu


@click.command(
    short_help="Otsu threshold",
    help="Applies the Otsu threshold",
)
@click.argument("raster", nargs=1)
def to_otsu(raster: str) -> None:
    """Apply Otsu threshold to one raster input."""
    run_otsu(raster)
