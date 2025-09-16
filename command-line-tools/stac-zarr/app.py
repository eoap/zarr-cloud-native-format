import click
import os
import pystac
from datetime import datetime
from loguru import logger
from odc.stac import stac_load
from pystac.extensions.datacube import DatacubeExtension
from shutil import move
import zarr

def extract_crs(item):
    """Extract CRS from a STAC item."""
    epsg = item.properties.get("proj:epsg")
    if epsg:
        return f"epsg:{epsg}"
    code = item.properties.get("proj:code")
    if code and code.upper().startswith("EPSG:"):
        return code.lower()  # "epsg:32633"
    raise ValueError("CRS not found in item properties")


def get_temporal_extent(items):
    """Get temporal extent from a list of STAC items."""
    times = [item.datetime for item in items]
    if not times:
        raise ValueError("No datetime found in item properties")
    return [min(times), max(times)]


def get_spatial_extent(items):
    """Get spatial extent from a list of STAC items."""
    bboxes = [item.bbox for item in items if item.bbox]
    if not bboxes:
        raise ValueError("No bbox found in item properties")
    min_x = min(bbox[0] for bbox in bboxes)
    min_y = min(bbox[1] for bbox in bboxes)
    max_x = max(bbox[2] for bbox in bboxes)
    max_y = max(bbox[3] for bbox in bboxes)
    return [min_x, min_y, max_x, max_y]


@click.command(
    short_help="Creates a zarr from a STAC catalog",
    help="Creates a zarr from STAC catalog with the water bodies",
)
@click.option(
    "--stac-catalog",
    "stac_catalog",
    help="STAC Catalog folder",
    required=True,
)
def to_zarr(stac_catalog):

    logger.info("Creating zarr from STAC catalog")

    logger.info(f"Reading STAC catalog from {stac_catalog}")
    cat = pystac.read_file(os.path.join(stac_catalog, "catalog.json"))

    items = list(cat.get_all_items())

    logger.info(f"STAC catalog contains {len(items)} items")
    crs = extract_crs(items[0])

    xx = stac_load(
        items,
        bands=["data"],
        crs=crs,
        resolution=10,
        chunks={"x": 512, "y": 512, "time": 1},
        groupby="time",
    )

    output_zarr = "result.zarr"

    xx.to_zarr(output_zarr, mode="w")
    zarr.consolidate_metadata(output_zarr)

    output_collection = pystac.Collection(
        id="water-bodies",
        description="Collection of detected water bodies",
        title="Detected water bodies",
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent(bboxes=[get_spatial_extent(items)]),
            temporal=pystac.TemporalExtent([get_temporal_extent(items)]),
        ),
    )

    dc_item = DatacubeExtension.ext(output_collection, add_if_missing=True)

    dc_item.dimensions = {
        "x": pystac.extensions.datacube.Dimension(
            properties={
                "type": "spatial",
                "axis": "x",
                "extent": [
                    float(min(xx.coords.get("x").values)),
                    float(max(xx.coords.get("x").values)),
                ],
                "reference_system": crs,
                "description": "X coordinate of projection",
            }
        ),
        "y": pystac.extensions.datacube.Dimension(
            properties={
                "type": "spatial",
                "axis": "y",
                "extent": [
                    float(min(xx.coords.get("y").values)),
                    float(max(xx.coords.get("y").values)),
                ],
                "reference_system": crs,
                "description": "Y coordinate of projection",
            }
        ),
        "time": pystac.extensions.datacube.Dimension(
            properties={
                "type": "temporal",
                "extent": [
                    str(min(xx.coords.get("time").values)),
                    str(max(xx.coords.get("time").values)),
                ],
                "description": "Time dimension",
            }
        ),
    }

    dc_item.variables = {
        "data": pystac.extensions.datacube.Variable(
            properties={
                "type": "data",
                "name": "water-bodies",
                "description": "detected water bodies",
                "dimensions": ["y", "x", "time"],
                "chunks": [512, 512, 1],
            }
        )
    }

    output_collection.add_asset(
        key="data",
        asset=pystac.Asset(
            href=output_zarr,
            media_type=pystac.MediaType.ZARR,
            roles=["data", "zarr"],
            title="Detected water bodies",
            description="Detected water bodies in Zarr cloud-native format",
            extra_fields={"xarray:open_kwargs": {"consolidated": True}},
        ),
    )

    os.makedirs(output_collection.id, exist_ok=True)

    # Move the zarr file to the item folder
    move(output_zarr, os.path.join(output_collection.id, output_zarr))

    output_cat = pystac.Catalog(
        id="water-bodies",
        description="Water bodies catalog",
        title="Water bodies catalog",
    )

    output_cat.add_child(output_collection)

    output_cat.normalize_and_save(
        root_href="./", catalog_type=pystac.CatalogType.SELF_CONTAINED
    )
    logger.info("Done!")


if __name__ == "__main__":
    to_zarr()
