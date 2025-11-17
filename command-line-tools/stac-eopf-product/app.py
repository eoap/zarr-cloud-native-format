from eopf.product import EOProduct, EOGroup, EOVariable
from eopf.store.zarr import EOZarrStore
import eopf.common.constants as c
import numpy as np
import click, os, pystac, zarr
from loguru import logger
from odc.stac import stac_load
from datetime import datetime

def extract_crs(item):
    """Extract CRS from a STAC item."""
    epsg = item.properties.get("proj:epsg")
    if epsg:
        return f"epsg:{epsg}"
    code = item.properties.get("proj:code")
    if code and code.upper().startswith("EPSG:"):
        return code.lower()  # "epsg:32633"
    raise ValueError("CRS not found in item properties")


@click.command()
@click.option("--stac-catalog", required=True)
def to_eopf(stac_catalog):

    logger.info("Reading STAC catalog")
    catalog = pystac.read_file(os.path.join(stac_catalog, "catalog.json"))
    items = list(catalog.get_all_items())

    logger.info(f"{len(items)} STAC items found")

    crs = extract_crs(items[0])

    # Load data as a single xarray dataset (same as before)
    xx = stac_load(
        items,
        bands=["data"],
        crs=crs,
        resolution=10,
        chunks={"x": 512, "y": 512, "time": 1},
        groupby="time",
    )

    logger.info("Loaded data using odc.stac")


    product = EOProduct(name="water_bodies_eopf")
    product["measurements"] = EOGroup()

    # Convert xarray array → EOVariable (Dask-aware)
    da = xx["data"]                      # (time, y, x)
    product["measurements/water"] = EOVariable(
        data=da.data,                    # dask array
        dims=("time", "y", "x"),
        attrs={"description": "Detected water bodies"}
    )

    spatial_bbox = [
        float(min(xx.x.values)), float(min(xx.y.values)),
        float(max(xx.x.values)), float(max(xx.y.values))
    ]

    temporal_extent = [
        str(xx.time.values.min()), 
        str(xx.time.values.max())
    ]


    product.attrs["stac_discovery"] = {
        "type": "Feature",
        "id": "water-bodies",
        "properties": {
            "start_datetime": temporal_extent[0],
            "end_datetime": temporal_extent[1],
        },
        "geometry": items[0].geometry,
        "bbox": items[0].bbox
    }

    out_dir = "./water_bodies_eopf"
    os.makedirs(out_dir)
    logger.info(f"Writing EOPF Zarr product → {out_dir}")

    with EOZarrStore(url=out_dir).open(mode=c.OpeningMode.CREATE_OVERWRITE) as store:
        store["water_bodies_eopf"] = product

    logger.info("Done writing EOPF product!")

if __name__ == "__main__":
    to_eopf()