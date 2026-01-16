import os
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
    SpatialExtent,
    STACObject,
    TemporalExtent,
    read_file as read_stac_file,
    Link,
)
from pystac.extensions.datacube import DatacubeExtension
from typing import List
from xarray import DataArray, Dataset
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterExtension, RasterBand
from datetime import datetime
import click
import zarr
from zarr.types import AnyArray
import dask.array


def extract_crs(item):
    """Extract CRS from a STAC item."""
    epsg = item.properties.get("proj:epsg")
    if epsg:
        return f"epsg:{epsg}"
    code = item.properties.get("proj:code")
    if code and code.upper().startswith("EPSG:"):
        return code.lower()  # "epsg:32633"
    raise ValueError("CRS not found in item properties")


def get_temporal_extent(items) -> List[datetime]:
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


def get_asset_keys(item: Item) -> List[str]:
    """Get asset keys from a STAC item."""
    return list(item.assets.keys())


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
def to_zarr(
    stac_catalog: Path,
):
    logger.info(f"Reading STAC catalog from {stac_catalog}...")
    catalog: STACObject = read_stac_file(os.path.join(stac_catalog, "catalog.json"))

    if not isinstance(catalog, Catalog):
        raise Exception(
            f"{stac_catalog} is not a valid STAC Catalog instance, found {type(catalog)}"
        )

    collection = next(catalog.get_children())
    if not isinstance(collection, Collection):
        raise Exception(
            f"{stac_catalog} does not contain a valid STAC Collection instance, found {type(collection)}"
        )

    items: List[Item] = list(collection.get_all_items())

    logger.info(f"Found {len(items)} STAC Items in {stac_catalog} STAC Catalog")
    crs = extract_crs(items[0])

    # Load data as a single xarray dataset (same as before)
    stac_catalog_dataset: Dataset = stac_load(
        items,
        bands=get_asset_keys(items[0]),
        crs=crs,
        resolution=10, # extract from item in future
        chunks={"x": 512, "y": 512, "time": 1},
        groupby="time",
    )

    logger.info("Loaded data using odc.stac")

    logger.info("Serializing the STAC Collection...")

    output_collection: Collection = Collection(
        id=collection.id,
        description=collection.description,
        title=collection.title,
        extent=Extent(
            spatial=SpatialExtent(bboxes=[get_spatial_extent(items)]),
            temporal=TemporalExtent([get_temporal_extent(items)]),
        ),
    )
    # adds extensions to the collection
    ProjectionExtension.summaries(output_collection, add_if_missing=True)
    RasterExtension.summaries(output_collection, add_if_missing=True)
    DatacubeExtension.ext(output_collection, add_if_missing=True)

    # Add Zarr store link
    zarr_uri = f"{collection.id}.zarr"

    output_collection.add_link(
        Link(
            rel="store",
            target=zarr_uri,
            media_type="application/vnd.zarr; version=3",
            title=f"Zarr store for {collection.title}",
        )
    )

    spatial_bbox = [
        float(min(stac_catalog_dataset.x.values)),
        float(min(stac_catalog_dataset.y.values)),
        float(max(stac_catalog_dataset.x.values)),
        float(max(stac_catalog_dataset.y.values)),
    ]

    # Create Zarr store

    measurement_name = "measurements"

    root = zarr.open_group(Path(collection.id, zarr_uri), mode="w")

    measurements_grp = root.require_group(measurement_name)

    bands = []
    cube_variables = {}
    raster_bands = []

    # Write each measurement (STAC asset) as a separate Zarr array
    for measurement in get_asset_keys(items[0]):
        logger.info(f"Writing measurement {measurement} to Zarr store...")
        da: DataArray = stac_catalog_dataset[measurement]
        # xarray -> zarr array
        da = da.transpose("time", "y", "x")

        title = (
            collection.item_assets[measurement].title
            if collection.item_assets and measurement in collection.item_assets
            else measurement
        )
        description = (
            collection.item_assets[measurement].description
            if collection.item_assets and measurement in collection.item_assets
            else measurement
        )

        z: AnyArray = measurements_grp.create(
            name=measurement,
            shape=da.shape,
            chunks=da.data.chunksize,
            dtype=da.dtype,
            overwrite=True,
            attributes={"title": title, "description": description},
            dimension_names=["time", "y", "x"],
        )

        # Write data
        dask.array.store(da.data, z, lock=True)

        bands.append(
            {
                "name": measurement,
                "description": description,
            }
        )

        cube_variables[measurement] = {
            "type": "data",
            "dimensions": ["time", "y", "x"],
        }

        # add raster band info
        raster_bands.append(
            RasterBand.create(
                data_type=da.dtype.name,  # "uint8", "float32", etc.
                nodata=None,
                spatial_resolution=[abs(da.x.values[1] - da.x.values[0]), abs(da.y.values[1] - da.y.values[0])],
            )
        )

    # create STAC Asset for the measurement
    logger.info(f"Creating STAC asset {zarr_uri}/measurements...")
    zarr_asset: Asset = Asset(
        href=f"{zarr_uri}/measurements",
        media_type="application/vnd.zarr; version=3",
        roles=["data"],
        title="Measurements",
        description="Zarr measurements group",
    )

    output_collection.add_asset(
        key="measurements",
        asset=zarr_asset,
    )

    # bands
    zarr_asset.extra_fields["bands"] = bands

    # datacube extension
    # workaround for datacube extension at asset level
    zarr_asset.extra_fields["cube:variables"] = cube_variables

    zarr_asset.extra_fields["cube:dimensions"] = {
        "time": {
            "type": "temporal",
            "extent": [
                get_temporal_extent(items)[0].isoformat().replace("+00:00", "Z"),
                get_temporal_extent(items)[1].isoformat().replace("+00:00", "Z"),
            ],
        },
        "x": {
            "type": "spatial",
            "axis": "x",
            "extent": [
                float(min(stac_catalog_dataset.x.values)),
                float(max(stac_catalog_dataset.x.values)),
            ],
        },
        "y": {
            "type": "spatial",
            "axis": "y",
            "extent": [
                float(min(stac_catalog_dataset.y.values)),
                float(max(stac_catalog_dataset.y.values)),
            ],
        },
    }

    # projection extension
    proj_ext = ProjectionExtension.ext(zarr_asset)

    gbox = stac_catalog_dataset.odc.geobox

    proj_ext.epsg = gbox.crs.epsg
    proj_ext.wkt2 = gbox.crs.to_wkt("WKT2_2019")
    proj_ext.shape = list(gbox.shape)
    proj_ext.transform = list(gbox.transform)

    proj_ext.bbox = spatial_bbox
    proj_ext.geometry = gbox.extent.to_crs(crs).json

    logger.info("Creating STAC Catalog for the output...")
    output_cat = Catalog(
        id=collection.id, description=collection.description, title=collection.title
    )

    # raster extension
    raster_ext = RasterExtension.ext(zarr_asset, add_if_missing=True)
    raster_ext.bands = raster_bands

    output_cat.add_child(output_collection)

    output_cat.normalize_and_save(
        root_href=str(Path(".")), catalog_type=CatalogType.SELF_CONTAINED
    )

    logger.info("Done!")


if __name__ == "__main__":
    to_zarr()
