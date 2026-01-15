import click
import os
import pystac
from loguru import logger
import shutil
import xarray as xr
import rio_stac
import pandas as pd
from pystac import Catalog, Collection, Asset

from affine import Affine
from pyproj import CRS

from odc.geo import GeoBox
from odc.geo.crs import CRS as OdcCRS


def attach_geobox_to_xarray(da: xr.DataArray, asset: Asset) -> xr.DataArray:
    """
    Attach CRS and transform from STAC metadata to an xarray DataArray.
    """

    affine = affine_from_stac_asset(asset)
    crs = crs_from_stac_asset(asset)

    da = da.rio.set_spatial_dims(x_dim="x", y_dim="y")
    da = da.rio.write_transform(affine)
    da = da.rio.write_crs(crs)

    return da


def geobox_from_stac_asset(asset: Asset) -> GeoBox:
    """
    Reconstruct an odc.geo.GeoBox from STAC Projection metadata.
    """

    shape = asset.extra_fields["proj:shape"]
    epsg = asset.extra_fields["proj:code"]

    affine = affine_from_stac_asset(asset)

    return GeoBox(
        shape=tuple(shape),
        affine=affine,
        crs=OdcCRS(epsg),
    )


def affine_from_stac_asset(asset: Asset) -> Affine:
    """
    Reconstruct an Affine transform from STAC Projection metadata.

    Assumes:
    - north-up grid
    - pixel-registered grid
    """

    bbox = asset.extra_fields["proj:bbox"]
    shape = asset.extra_fields["proj:shape"]

    xmin, ymin, xmax, ymax = bbox
    height, width = shape

    xres = (xmax - xmin) / width
    yres = (ymax - ymin) / height

    # GDAL / rasterio convention: origin is upper-left
    return Affine(xres, 0.0, xmin, 0.0, -yres, ymax)


def crs_from_stac_asset(asset: Asset) -> CRS:
    """
    Extract CRS from STAC Projection metadata.
    """

    epsg = asset.extra_fields.get("proj:code")
    if not epsg:
        raise ValueError("Asset is missing proj:code")

    return CRS.from_user_input(epsg)


@click.command(
    short_help="Derives water occurrence from datacube encoded in the Zarr format",
    help="Creates a zarr from STAC catalog with the water bodies",
)
@click.option(
    "--stac-catalog",
    "stac_catalog",
    help="STAC Catalog folder",
    required=True,
)
def occurrence(stac_catalog):
    logger.info("Water occurrence")

    logger.info(f"Reading STAC catalog from {stac_catalog}")

    src_cat: Catalog = pystac.Catalog.from_file(
        os.path.join(stac_catalog, "catalog.json")
    )

    collection: Collection = next(src_cat.get_children())

    measurements: Asset = collection.get_assets()["measurements"]

    water_bodies = xr.open_zarr(measurements.get_absolute_href(), consolidated=False)[
        "water-bodies"
    ]

    mean = water_bodies.mean("time")
    mean = attach_geobox_to_xarray(mean, asset=measurements)
    mean.rio.to_raster("water_bodies_mean.tif")

    logger.info("Creating a STAC Catalog for the output")
    cat = pystac.Catalog(id="catalog", description="water-bodies-mean")

    item_id = "occurrence"
    os.makedirs(item_id, exist_ok=True)
    shutil.copy("water_bodies_mean.tif", item_id)

    out_item = rio_stac.stac.create_stac_item(
        source="water_bodies_mean.tif",
        input_datetime=collection.extent.temporal.intervals[0][1],
        id=item_id,
        asset_roles=["data", "visual"],
        asset_href=os.path.basename("water_bodies_mean.tif"),
        asset_name="data",
        with_proj=True,
        with_raster=True,
    )

    os.remove("water_bodies_mean.tif")

    cat.add_items([out_item])

    cat.normalize_and_save(
        root_href="./", catalog_type=pystac.CatalogType.SELF_CONTAINED
    )
    logger.info("Done!")


if __name__ == "__main__":
    occurrence()
