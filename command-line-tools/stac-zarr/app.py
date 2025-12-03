from datetime import datetime
from loguru import logger
from odc.stac import stac_load
from pathlib import Path
from pystac import (
    Asset,
    Catalog,
    CatalogType,
    Collection,
    Extent,
    Item,
    MediaType,
    SpatialExtent,
    STACObject,
    TemporalExtent,
    read_file as read_stac_file
)
from pystac.extensions.datacube import (
    DatacubeExtension,
    Dimension,
    Variable
)
from shutil import move
from typing import (
    Any,
    List
)
from xarray import Dataset

import click
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
    type=click.Path(
        path_type=Path,
        exists=True,
        readable=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True
    ),
    help="STAC Catalog file",
    required=True,
)
@click.option(
    "--collection-id",
    type=click.STRING,
    required=True,
    help="The target STAC Collection ID",
)
@click.option(
    "--output-dir",
    type=click.Path(
        path_type=Path,
        exists=True,
        readable=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    ),
    default=Path('.'),
    required=True,
    help="Output directory path",
)
def to_zarr(
    stac_catalog: Path,
    collection_id: str,
    output_dir: Path
):
    logger.info(f"Reading STAC catalog from {stac_catalog}...")
    cat: STACObject = read_stac_file(stac_catalog)

    if not isinstance(cat, Catalog):
        raise Exception(f"{stac_catalog} is not a valid STAC Catalog instance, found {type(cat)}")

    items: List[Item] = list(cat.get_all_items())

    logger.info(f"Found {len(items)} STAC Items in {stac_catalog} STAC Catalog")
    crs = extract_crs(items[0])

    stac_catalog_dataset: Dataset = stac_load(
        items,
        bands=["data"],
        crs=crs,
        resolution=10,
        chunks={"x": 512, "y": 512, "time": 1},
        groupby="time",
    )

    output_collection: Collection = Collection(
        id=collection_id,
        description=f"Collection of detected {collection_id}",
        title=f"Detected {collection_id}",
        extent=Extent(
            spatial=SpatialExtent(bboxes=[get_spatial_extent(items)]),
            temporal=TemporalExtent([get_temporal_extent(items)]),
        ),
    )

    output_collection_dir = Path(output_dir, output_collection.id)

    output_collection_dir.mkdir(parents=True, exist_ok=True)
    output_zarr: Path = Path(output_collection_dir, "result.zarr")

    stac_catalog_dataset.to_zarr(output_zarr, mode="w")
    zarr.consolidate_metadata(output_zarr)

    # Datacube Extension v2.x

    dc_item = DatacubeExtension.ext(output_collection, add_if_missing=True)

    def _get_values(name: str) -> Any:
        return stac_catalog_dataset.coords.get(name).values # type: ignore

    def _get_min(name: str) -> Any:
        return min(_get_values(name))

    def _get_max(name: str) -> Any:
        return max(_get_values(name))

    dc_item.dimensions = {
        "x": Dimension(
            properties={
                "type": "spatial",
                "axis": "x",
                "extent": [
                    float(_get_min("x")),
                    float(_get_max("x")),
                ],
                "reference_system": crs,
                "description": "X coordinate of projection",
            }
        ),
        "y": Dimension(
            properties={
                "type": "spatial",
                "axis": "y",
                "extent": [
                    float(_get_min("y")),
                    float(_get_max("y")),
                ],
                "reference_system": crs,
                "description": "Y coordinate of projection",
            }
        ),
        "time": Dimension(
            properties={
                "type": "temporal",
                "extent": [
                    str(_get_min("time")),
                    str(_get_max("time")),
                ],
                "description": "Time dimension",
            }
        ),
    }

    dc_item.variables = {
        "data": Variable(
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
        asset=Asset(
            href=output_zarr.name,
            media_type=f"{MediaType.ZARR}; version=3",
            roles=["data", "zarr"],
            title="Detected water bodies",
            description="Detected water bodies in Zarr cloud-native format",
            extra_fields={"xarray:open_kwargs": {"consolidated": True}},
        ),
    )

    output_cat = Catalog(
        id="water-bodies",
        description="Water bodies catalog",
        title="Water bodies catalog",
    )

    output_cat.add_child(output_collection)

    output_cat.normalize_and_save(
        root_href=str(output_dir.absolute()),
        catalog_type=CatalogType.SELF_CONTAINED
    )
    logger.info("Done!")


if __name__ == "__main__":
    to_zarr()
