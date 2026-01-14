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
from pystac.extensions.raster import RasterExtension
import click
import zarr
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
        resolution=10,
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
    # ----------------------------
    # Add Zarr store link
    # ----------------------------
    zarr_store = collection.id

    output_collection.add_link(
        Link(
            rel="store",
            target=f"{zarr_store}.zarr",
            media_type="application/vnd.zarr; version=3",
            title=collection.title,
        )
    )

    spatial_bbox = [
        float(min(stac_catalog_dataset.x.values)),
        float(min(stac_catalog_dataset.y.values)),
        float(max(stac_catalog_dataset.x.values)),
        float(max(stac_catalog_dataset.y.values)),
    ]

    # Create Zarr store
    zarr_uri = f"{collection.id}.zarr"
    measurement_name = "measurements"

    root = zarr.open_group(Path(collection.id, zarr_uri), mode="w")

    measurements_grp = root.require_group(measurement_name)

    # Convert xarray array → EOVariable (Dask-aware)
    for measurement in get_asset_keys(items[0]):
        da: DataArray = stac_catalog_dataset[measurement]
        da = da.transpose("time", "y", "x")
        # xarray → zarr array
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

        z = measurements_grp.create(
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

        # create STAC Asset for the measurement
        zarr_asset = Asset(
            href=f"{zarr_store}.zarr/measurements",
            media_type="application/vnd.zarr; version=2",
            roles=["data", "zarr"],
            title=title,  # collection item-asset title
            description=description,  # collection item-asset description
        )

        output_collection.add_asset(
            key=measurement,
            asset=zarr_asset,
        )

        zarr_asset.extra_fields["bands"] = [
            {
                "name": measurement,  # collection item-asset title
                "description": description,  # collection item-asset description
            }
        ]

        # workaround for datacube extension at asset level
        zarr_asset.extra_fields["cube:variables"] = {
            measurement: {
                "type": "data",
                "dimensions": list(stac_catalog_dataset[measurement].dims),
            }
        }

        zarr_asset.extra_fields["cube:dimensions"] = {
            "time": {
                "type": "temporal",
                "extent": [
                    get_temporal_extent(items)[0].isoformat() + "Z",
                    get_temporal_extent(items)[1].isoformat() + "Z",
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

        proj_ext = ProjectionExtension.ext(zarr_asset)

        gbox = stac_catalog_dataset.odc.geobox
        proj_ext.epsg = gbox.crs.epsg  # or any EPSG integer
        proj_ext.bbox = spatial_bbox  # in the asset CRS

        extent = gbox.extent
        footprint_wgs84 = extent.to_crs(crs)
        proj_ext.geometry = footprint_wgs84.json  # GeoJSON in the asset CRS

        height, width = gbox.shape
        proj_ext.shape = [height, width]

    output_cat = Catalog(
        id=collection.id, description=collection.description, title=collection.title
    )

    output_cat.add_child(output_collection)

    output_cat.normalize_and_save(
        root_href=str(Path(".")), catalog_type=CatalogType.SELF_CONTAINED
    )

    output_zarr = Path(zarr_uri)
    logger.info(f"Written Zarr store to {output_zarr}")

    logger.info("Done!")


if __name__ == "__main__":
    to_zarr()
