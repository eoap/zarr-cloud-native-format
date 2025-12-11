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
    Item,
    MediaType,
    STACObject,
    read_file as read_stac_file,
    write_file as write_stac_file
)
from pystac.extensions.datacube import (
    DatacubeExtension,
    DimensionType,
    HorizontalSpatialDimension,
    HorizontalSpatialDimensionAxis,
    TemporalDimension,
    Variable,
    VariableType
)
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import (
    RasterExtension,
    RasterBand,
    DataType
)
from shapely.geometry import (
    mapping,
    shape
)
from typing import (
    Any,
    List
)
from xarray import (
    DataArray,
    Dataset
)

import eopf.common.constants as c
import numpy as np
import click, os, pystac, zarr
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


@click.command()
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
    "--output-dir",
    type=click.Path(
        path_type=Path,
        exists=False,
        readable=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    ),
    default=Path('.'),
    required=True,
    help="Output directory path",
)
def to_eopf(
    stac_catalog: Path,
    output_dir: Path
):
    logger.info(f"Reading STAC catalog from {stac_catalog}...")
    catalog: STACObject = read_stac_file(stac_catalog)

    if not isinstance(catalog, Catalog):
        raise Exception(f"{stac_catalog} is not a valid STAC Catalog instance, found {type(catalog)}")

    items: List[Item] = list(catalog.get_all_items())

    logger.info(f"Found {len(items)} STAC Items in {stac_catalog} STAC Catalog")
    crs = extract_crs(items[0])

    # Load data as a single xarray dataset (same as before)
    stac_catalog_dataset: Dataset = stac_load(
        items,
        bands=["data"],
        crs=crs,
        resolution=10,
        chunks={"x": 512, "y": 512, "time": 1},
        groupby="time",
    )

    logger.info("Loaded data using odc.stac")

    product: EOProduct = EOProduct(name="water_bodies_eopf")
    product["measurements"] = EOGroup()

    # Convert xarray array → EOVariable (Dask-aware)
    da = stac_catalog_dataset["data"]                      # (time, y, x)
    product["measurements/water"] = EOVariable(
        data=da.data,                    # dask array
        dims=("time", "y", "x"),
        attrs={"description": "Detected water bodies"}
    )

    spatial_bbox = [
        float(min(stac_catalog_dataset.x.values)),
        float(min(stac_catalog_dataset.y.values)),
        float(max(stac_catalog_dataset.x.values)),
        float(max(stac_catalog_dataset.y.values))
    ]

    start_datetime = _to_datetime(stac_catalog_dataset.time.values.min())
    end_datetime = _to_datetime(stac_catalog_dataset.time.values.max())

    item: Item = Item(
        id="water-bodies",
        geometry=items[0].geometry,
        bbox=spatial_bbox,
        datetime=start_datetime,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        properties={}
    )

    product.attrs["stac_discovery"] = item.to_dict(include_self_link=False)

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing EOPF Zarr product to {output_dir}")

    with EOZarrStore(
        url=output_dir.absolute().as_uri()
    ).open(
        mode=c.OpeningMode.CREATE_OVERWRITE
    ) as store:
        store["water_bodies_eopf"] = product

    logger.info("Done writing EOPF product! Serializing the STAC Item...")

    item.add_asset(
        key="store",
        asset=Asset(
            href="water_bodies_eopf.zarr",
            media_type=f"{MediaType.ZARR}; version=3",
            roles=["data", "zarr"],
            title="Zarr Store",
            description="Detected water bodies in Zarr cloud-native format"
        )
    )

    item.add_asset(
        key="data-variable",
        asset=Asset(
            href="water_bodies_eopf.zarr/measurements/{measurement}",
            media_type=f"{MediaType.ZARR}; version=3",
            roles=["data", "zarr"],
            title="Detected water bodies",
            description="Detected water bodies in Zarr cloud-native format",
            extra_fields={
                "variables": {
                    "measurement": {
                        "type": "string",
                        "enum": [str(group) for group in product["measurements"]]
                    }
                }
            },
        )
    )

    # DataCube

    dc = DatacubeExtension.ext(item, add_if_missing=True)

    x_dim = HorizontalSpatialDimension({})
    x_dim.dim_type = DimensionType.SPATIAL
    x_dim.axis = HorizontalSpatialDimensionAxis.X
    x_dim.description = "X coordinate of projection"
    x_dim.extent = [spatial_bbox[0], spatial_bbox[2]]           # [min, max]
    # x_dim.step = 10.0                             # pixel size
    x_dim.reference_system = crs

    y_dim = HorizontalSpatialDimension({})
    y_dim.dim_type = DimensionType.SPATIAL
    y_dim.axis = HorizontalSpatialDimensionAxis.Y
    y_dim.extent = [spatial_bbox[1], spatial_bbox[3]]
    # y_dim.step = 10.0
    y_dim.reference_system = crs

    t_dim = TemporalDimension({})
    t_dim.dim_type = DimensionType.TEMPORAL
    t_dim.extent = [start_datetime.isoformat(), end_datetime.isoformat()]

    water_bodies_variables = Variable({})
    water_bodies_variables.var_type = VariableType.DATA
    water_bodies_variables.dimensions = ["x", "y", "time"]
    #water_bodies_variables.unit = "1"
    water_bodies_variables.description = "detected water bodies"

    dc.apply(dimensions={
        "x": x_dim,
        "y": y_dim,
        "time": t_dim
    }, variables={
        "water-bodies": water_bodies_variables
    })

    # Projection

    gbox = stac_catalog_dataset.odc.geobox

    proj = ProjectionExtension.ext(item, add_if_missing=True)
    proj.epsg = gbox.crs.epsg # or any EPSG integer
    proj.bbox = spatial_bbox # in the asset CRS

    extent = gbox.extent
    footprint_wgs84 = extent.to_crs(crs)
    proj.geometry = footprint_wgs84.json  # GeoJSON in the asset CRS

    height, width = gbox.shape
    proj.shape = [height, width]         # pixels (rows, cols)
    #proj.transform = list(affine_geotransform)  # GDAL-style 6 or 9 numbers

    # Optionally, centroid in projected coordinates
    #proj.centroid = {"x": cx, "y": cy}

    # Raster extension
    RasterExtension.add_to(item)  # adds schema URI to stac_extensions

    # 2. Determine which variables map to bands
    band_var_names = list(stac_catalog_dataset.data_vars.keys())

    bands: list[RasterBand] = []
    for var_name in band_var_names:
        da = stac_catalog_dataset[var_name]
        band = raster_band_from_dataarray(da)
        bands.append(band)

    # 3. Attach raster:bands to the asset

    item.add_asset(
        key="raster",
        asset=Asset(
            href="to-be-defined",
            media_type=f"{MediaType.ZARR}; version=3",
            roles=["data", "zarr"],
            title="Raster Data",
            description="Raster data derived from xarray.Dataset"
        )
    )
    raster_ext = RasterExtension.ext(item.assets["raster"], add_if_missing=True)
    raster_ext.bands = bands


    output_item: Path = Path(output_dir, 'item.json')
    write_stac_file(
        obj=item,
        include_self_link=True,
        dest_href=output_item
    )

if __name__ == "__main__":
    to_eopf()