import click
import os
import pystac
from datetime import datetime
from loguru import logger
from odc.stac import stac_load
from pystac.extensions.datacube import DatacubeExtension


@click.command(
    short_help="Creates a zarr from a STAC catalog",
    help="Creates a zarr from STAC catalog with the water bodies",
)
@click.option(
    "--stac-catalog",
    "stac_catalog",
    help="STAC Catalog folder",
    required=True,
    multiple=False,
)
def to_zarr(stac_catalog):

    logger.info("Creating zarr from STAC catalog")

    logger.info(f"Reading STAC catalog from {stac_catalog}")
    cat = pystac.read_file(os.path.join(stac_catalog, "catalog.json"))

    items = list(cat.get_all_items())

    logger.info(f"STAC catalog contains {len(items)} items")
    crs = f"epsg:{items[0].properties['proj:epsg']}"

    xx = stac_load(
        items,
        bands=("data"),
        crs=crs,
        resolution=10, # * zoom,
        chunks={},  # <-- use Dask
        groupby="time",
    )

    output_zarr = "result.zarr"

    xx.to_zarr(output_zarr, mode="w")

    output_item = pystac.Item(id="water-bodies", geometry=items[0].geometry, bbox=items[0].bbox, datetime=datetime.now(), properties={"proj:epsg": crs})

    dc_item  = DatacubeExtension.ext(output_item, add_if_missing=True)

    dc_item.dimensions = {
        "x": pystac.extensions.datacube.Dimension(properties={
            "type":"spatial",
            "axis":"x",
            "extent":[float(min(xx.coords.get("x").values)), float(max(xx.coords.get("x").values))],
            "reference_system": crs
    }),"y": pystac.extensions.datacube.Dimension(properties={
            "type":"spatial",
            "axis":"y",
            "extent":[float(min(xx.coords.get("y").values)), float(max(xx.coords.get("y").values))], 
            "reference_system": crs
    }),
    "time": pystac.extensions.datacube.Dimension(properties={
            "type":"temporal",
            "extent":[str(min(xx.coords.get("time").values)), str(max(xx.coords.get("time").values))],  
    })}

    dc_item.variables = {"data": pystac.extensions.datacube.Variable(properties={"type": "bands", "description": "water bodies", "dimensions": ["y", "x", "time"]})}

    output_item.add_asset(key="data", asset=pystac.Asset(href=output_zarr, media_type=pystac.MediaType.ZARR, roles=["data"]))

    output_cat = pystac.Catalog(id="water-bodies", description="Water bodies catalog", title="Water bodies catalog")

    output_cat.add_items([output_item])

    output_cat.normalize_and_save(
        root_href="./", catalog_type=pystac.CatalogType.SELF_CONTAINED
    )
    logger.info("Done!")


if __name__ == "__main__":
    to_zarr()