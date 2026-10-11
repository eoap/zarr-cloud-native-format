import click

from norm_diff_tool.writer import run_norm_diff


@click.command(
    short_help="Normalized difference",
    help="Performs a normalized difference",
)
@click.argument("rasters", nargs=2)
def to_norm_diff(rasters: tuple[str, str]) -> None:
    """Compute normalized difference from two raster inputs."""
    run_norm_diff(rasters[0], rasters[1])

