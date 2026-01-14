import os
from datetime import (
    datetime,
    timezone
)
from eopf.product import (
    EOProduct,
    EOGroup,
    EOVariable
)
from eopf.store.zarr import EOZarrStore

from pathlib import Path
from pystac import (
    Asset,
    Catalog,
    Collection,
    Extent,
    SpatialExtent,
    TemporalExtent,
    Item,
    STACObject,
    CatalogType,
    read_file as read_stac_file
)
from pystac.extensions.datacube import (
    DatacubeExtension
)
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import (
    RasterExtension,
    RasterBand,
    DataType
)
from typing import (
    List
)
from xarray import (
    DataArray,
    Dataset
)

import eopf.common.constants as c
import numpy as np
import click
import pystac
from loguru import logger
from odc.stac import stac_load

DTYPE_TO_RASTER = {
    np.dtype("int8"): DataType.INT8,
    np.dtype("int16"): DataType.INT16,
    np.dtype("int32"): DataType.INT32,
    np.dtype("int64"): DataType.INT64,
    np.dtype("uint8"): DataType.UINT8,
    np.dtype("uint16"): DataType.UINT16,
    np.dtype("uint32"): DataType.UINT32,
    np.dtype("uint64"): DataType.UINT64,
    np.dtype("float16"): DataType.FLOAT16,
    np.dtype("float32"): DataType.FLOAT32,
    np.dtype("float64"): DataType.FLOAT64,
}

def to_raster_datatype(dtype: np.dtype) -> DataType:
    return DTYPE_TO_RASTER.get(np.dtype(dtype), DataType.OTHER)

def raster_band_from_dataarray(da: DataArray) -> RasterBand:
    nodata = (
        da.encoding.get("_FillValue")
        or da.attrs.get("_FillValue")
        or da.attrs.get("nodata")
    )

    scale = da.encoding.get("scale_factor") or da.attrs.get("scale_factor")
    offset = da.encoding.get("add_offset") or da.attrs.get("add_offset")
    unit = da.attrs.get("units")

    # Optional spatial resolution (if you have it)
    spatial_resolution = None
    if hasattr(da, "rio"):
        try:
            # rioxarray: returns (xres, yres)
            xres, yres = da.rio.resolution()
            # STAC raster extension expects a single number; you can choose x or y,
            # or store both in statistics / custom metadata if you prefer.
            spatial_resolution = abs(xres)
        except Exception:
            pass

    band = RasterBand.create(
        data_type=to_raster_datatype(da.dtype),
        nodata=nodata,
        scale=scale,
        offset=offset,
        unit=unit,
        spatial_resolution=spatial_resolution,
        # You can also fill statistics here if you want:
        # statistics=RasterStatistics.create(
        #     minimum=float(da.min().values),
        #     maximum=float(da.max().values),
        #     mean=float(da.mean().values),
        #     stddev=float(da.std().values),
        # ),
    )

    return band


def extract_crs(item):
    """Extract CRS from a STAC item."""
    epsg = item.properties.get("proj:epsg")
    if epsg:
        return f"epsg:{epsg}"
    code = item.properties.get("proj:code")
    if code and code.upper().startswith("EPSG:"):
        return code.lower()  # "epsg:32633"
    raise ValueError("CRS not found in item properties")


def _to_datetime(npdatetime):
    ns = npdatetime.astype("datetime64[ns]").astype("int64")

    # datetime has microsecond resolution, so split seconds / microseconds
    seconds = ns // 1_000_000_000
    micros = (ns % 1_000_000_000) // 1_000

    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(microsecond=int(micros))

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


@click.command()
@click.option(
    "--stac-catalog",
    type=click.Path(
        path_type=Path,
        exists=True,
        readable=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    ),
    help="STAC Catalog file",
    required=True,
)
def to_eopf(
    stac_catalog: Path,
):
    logger.info(f"Reading STAC catalog from {stac_catalog}...")
    catalog: STACObject = read_stac_file(os.path.join(stac_catalog, "catalog.json"))

    if not isinstance(catalog, Catalog):
        raise Exception(f"{stac_catalog} is not a valid STAC Catalog instance, found {type(catalog)}")

    collection = next(catalog.get_children())
    if not isinstance(collection, Collection):
        raise Exception(f"{stac_catalog} does not contain a valid STAC Collection instance, found {type(collection)}")

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

    logger.info("Done writing EOPF product! Serializing the STAC Collection...")

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
        pystac.Link(
            rel="store",
            target=f"{zarr_store}.zarr",
            media_type="application/vnd.zarr; version=2",
            title=collection.title,
        )
    )

    spatial_bbox = [
        float(min(stac_catalog_dataset.x.values)),
        float(min(stac_catalog_dataset.y.values)),
        float(max(stac_catalog_dataset.x.values)),
        float(max(stac_catalog_dataset.y.values))
    ]

    product: EOProduct = EOProduct(name=collection.id)
    product["measurements"] = EOGroup()

    # Convert xarray array → EOVariable (Dask-aware)
    for measurement in get_asset_keys(items[0]):
        da = stac_catalog_dataset[measurement]                      # (time, y, x)
        product[f"measurements/{measurement}"] = EOVariable(
            data=da.data,                    # dask array
            dims=stac_catalog_dataset[measurement].dims,
            attrs={"description": collection.item_assets[measurement].description if collection.item_assets and measurement in collection.item_assets else "", }
        )

        title = collection.item_assets[measurement].title if collection.item_assets and measurement in collection.item_assets else measurement
        description = collection.item_assets[measurement].description if collection.item_assets and measurement in collection.item_assets else measurement

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
                "description": description  # collection item-asset description
            }
        ]

        # workaround for datacube extension at asset level
        zarr_asset.extra_fields["cube:variables"] = {
            measurement: {
                "type": "data",
                "dimensions": list(stac_catalog_dataset[measurement].dims)
            }
        }

        zarr_asset.extra_fields["cube:dimensions"] = {
            "time": {
                "type": "temporal",
                "extent": [
                    get_temporal_extent(items)[0].isoformat() + "Z",
                    get_temporal_extent(items)[1].isoformat() + "Z",
                ]
            },
            "x": {"type": "spatial", "axis": "x", "extent": [
                    float(min(stac_catalog_dataset.x.values)),
                    float(max(stac_catalog_dataset.x.values))
                ]},
            "y": {"type": "spatial", "axis": "y", "extent": [
                    float(min(stac_catalog_dataset.y.values)),
                    float(max(stac_catalog_dataset.y.values))
                ]}
        }

        # when pystac datacube extension supports asset level, use this:
        # dc_ext = DatacubeExtension.ext(zarr_asset)

        # dc_ext.cube_variables = {
        #     "water-bodies": {
        #         "type": "data",
        #         "dimensions": ["time", "y", "x"]
        #     }
        # }

        # dc_ext.cube_dimensions = {
        #     "time": {
        #         "type": "temporal",
        #         "extent": [
        #             get_temporal_extent(items)[0].isoformat() + "Z",
        #             get_temporal_extent(items)[1].isoformat() + "Z",
        #         ],
        #     },
        #     "x": {
        #         "type": "spatial",
        #         "axis": "x",
        #         "extent": [
        #             float(min(stac_catalog_dataset.x.values)),
        #             float(max(stac_catalog_dataset.x.values))
        #         ]
        #     },
        #     "y": {
        #         "type": "spatial",
        #         "axis": "y",
        #         "extent": [
        #             float(min(stac_catalog_dataset.y.values)),
        #             float(max(stac_catalog_dataset.y.values))
        #         ]
        #     },
        # }

        proj_ext = ProjectionExtension.ext(zarr_asset)

        gbox = stac_catalog_dataset.odc.geobox
        proj_ext.epsg = gbox.crs.epsg # or any EPSG integer
        proj_ext.bbox = spatial_bbox # in the asset CRS

        extent = gbox.extent
        footprint_wgs84 = extent.to_crs(crs)
        proj_ext.geometry = footprint_wgs84.json  # GeoJSON in the asset CRS

        height, width = gbox.shape
        proj_ext.shape = [height, width]

    output_cat = Catalog(
        id=collection.id,
        description=collection.description,
        title=collection.title
    )

    output_cat.add_child(output_collection)



    output_cat.normalize_and_save(
        root_href=str(Path(".")),
        catalog_type=CatalogType.SELF_CONTAINED
    )

    output_dir = Path(collection.id)
    logger.info(f"Creating output directory at {output_dir.absolute()}")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing EOPF Zarr product to {output_dir}")
   
    with EOZarrStore(
        url=output_dir.absolute().as_uri()
    ).open(
        mode=c.OpeningMode.CREATE_OVERWRITE
    ) as store:
        store[zarr_store] = product
    logger.info("Done writing EOPF product!")


if __name__ == "__main__":
    to_eopf()