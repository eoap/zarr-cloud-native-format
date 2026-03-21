import click

from crop_tool.writer import run_crop


@click.command(
    short_help="Crop",
    help="Crops a STAC Item asset defined with its common band name",
)
@click.option(
    "--input-item",
    "item_url",
    help="STAC Item URL or staged STAC catalog",
    required=True,
)
@click.option(
    "--aoi",
    "aoi",
    help="Area of interest expressed as a bounding box",
    required=True,
)
@click.option(
    "--epsg",
    "epsg",
    help="EPSG code",
    required=True,
)
@click.option(
    "--band",
    "band",
    help="Common band name",
    required=True,
)
@click.option(
    "--asset-signing",
    "asset_signing",
    type=click.Choice(["auto", "none", "mspc"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Asset HREF signing strategy for cloud providers.",
)
def to_crop(item_url: str, aoi: str, epsg: str, band: str, asset_signing: str) -> None:
    run_crop(item_url=item_url, aoi=aoi, band=band, epsg=epsg, asset_signing=asset_signing)
