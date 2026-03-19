import os
from pathlib import Path
from typing import Any, Dict, List

import eopf.common.constants as c
import numpy as np
import pystac
from eopf.product import EOGroup, EOProduct, EOVariable
from eopf.store.zarr import EOZarrStore
from loguru import logger
from odc.stac import stac_load
from pystac import (
    Asset,
    Catalog,
    CatalogType,
    Collection,
    Item,
    STACObject,
    read_file as read_stac_file,
)
from pystac.extensions.datacube import DatacubeExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import DataType, RasterBand, RasterExtension
from xarray import DataArray, Dataset

from stac_eopf_product.contract import (
    extract_crs,
    get_measurement_keys,
    get_spatial_extent,
    get_temporal_extent,
    validate_items_have_measurements,
)
from stac_eopf_product.metadata import (
    build_cube_dimensions,
    build_output_collection,
    get_measurement_text,
)

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
    nodata = da.encoding.get("_FillValue") or da.attrs.get("_FillValue") or da.attrs.get("nodata")
    scale = da.encoding.get("scale_factor") or da.attrs.get("scale_factor")
    offset = da.encoding.get("add_offset") or da.attrs.get("add_offset")
    unit = da.attrs.get("units")
    spatial_resolution = None
    if hasattr(da, "rio"):
        try:
            xres, _yres = da.rio.resolution()
            spatial_resolution = abs(xres)
        except Exception:
            pass

    return RasterBand.create(
        data_type=to_raster_datatype(da.dtype),
        nodata=nodata,
        scale=scale,
        offset=offset,
        unit=unit,
        spatial_resolution=spatial_resolution,
    )


def build_stac_load_kwargs(
    bands: List[str],
    crs: str,
    resolution: float | None,
    chunks: str,
    chunk_x: int,
    chunk_y: int,
    chunk_time: int,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "bands": bands,
        "crs": crs,
        "groupby": "time",
    }
    if chunks == "manual":
        kwargs["chunks"] = {"x": chunk_x, "y": chunk_y, "time": chunk_time}
    if resolution is not None:
        kwargs["resolution"] = resolution
    return kwargs


def run_to_eopf(
    stac_catalog: Path,
    resolution: float | None = None,
    chunks: str = "manual",
    chunk_x: int = 512,
    chunk_y: int = 512,
    chunk_time: int = 1,
) -> None:
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
    if not items:
        raise ValueError("Input STAC Collection has no items")

    crs = extract_crs(items[0])
    temporal_extent = get_temporal_extent(items)
    measurement_keys = get_measurement_keys(collection)
    validate_items_have_measurements(items, measurement_keys)

    stac_catalog_dataset: Dataset = stac_load(
        items,
        **build_stac_load_kwargs(
            bands=measurement_keys,
            crs=crs,
            resolution=resolution,
            chunks=chunks,
            chunk_x=chunk_x,
            chunk_y=chunk_y,
            chunk_time=chunk_time,
        ),
    )

    logger.info("Loaded data using odc.stac")
    logger.info("Done writing EOPF product! Serializing the STAC Collection...")

    output_collection: Collection = build_output_collection(
        input_collection=collection,
        spatial_extent=get_spatial_extent(items),
        temporal_extent=temporal_extent,
    )
    ProjectionExtension.summaries(output_collection, add_if_missing=True)
    RasterExtension.summaries(output_collection, add_if_missing=True)
    DatacubeExtension.ext(output_collection, add_if_missing=True)

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
        float(max(stac_catalog_dataset.y.values)),
    ]

    product: EOProduct = EOProduct(name=collection.id)
    product["measurements"] = EOGroup()

    for measurement in measurement_keys:
        da: DataArray = stac_catalog_dataset[measurement]
        product[f"measurements/{measurement}"] = EOVariable(
            data=da.data,
            dims=stac_catalog_dataset[measurement].dims,
            attrs={
                "description": get_measurement_text(collection, measurement)[1],
            },
        )

        title, description = get_measurement_text(collection, measurement)

        zarr_asset = Asset(
            href=f"{zarr_store}.zarr/measurements",
            media_type="application/vnd.zarr; version=2",
            roles=["data", "zarr"],
            title=title,
            description=description,
        )
        output_collection.add_asset(key=measurement, asset=zarr_asset)

        zarr_asset.extra_fields["bands"] = [{"name": measurement, "description": description}]
        zarr_asset.extra_fields["cube:variables"] = {
            measurement: {
                "type": "data",
                "dimensions": list(stac_catalog_dataset[measurement].dims),
            }
        }
        zarr_asset.extra_fields["cube:dimensions"] = build_cube_dimensions(
            stac_catalog_dataset, temporal_extent
        )

        proj_ext = ProjectionExtension.ext(zarr_asset)
        gbox = stac_catalog_dataset.odc.geobox
        proj_ext.epsg = gbox.crs.epsg
        proj_ext.bbox = spatial_bbox
        proj_ext.geometry = gbox.extent.to_crs(crs).json
        height, width = gbox.shape
        proj_ext.shape = [height, width]

    output_cat = Catalog(id=collection.id, description=collection.description, title=collection.title)
    output_cat.add_child(output_collection)
    output_cat.normalize_and_save(root_href=str(Path(".")), catalog_type=CatalogType.SELF_CONTAINED)

    output_dir = Path(collection.id)
    logger.info(f"Creating output directory at {output_dir.absolute()}")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing EOPF Zarr product to {output_dir}")

    with EOZarrStore(url=output_dir.absolute().as_uri()).open(mode=c.OpeningMode.CREATE_OVERWRITE) as store:
        store[zarr_store] = product
    logger.info("Done writing EOPF product!")
