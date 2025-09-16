import click
import os
import pystac
from loguru import logger
from pystac.extensions.datacube import DatacubeExtension
import shutil
import xarray as xr
import rioxarray
import rio_stac
import pandas as pd


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

    cat = pystac.Catalog.from_file(os.path.join(stac_catalog, "catalog.json"))

    collection = cat.get_child("water-bodies")

    dc_collection = DatacubeExtension.ext(collection)

    for key, dim in dc_collection.dimensions.items():
        logger.info(f"Dimension: {key}, Type: {dim.dim_type}, Extent: {dim.extent}")

    for key, variable in dc_collection.variables.items():
        logger.info(
            f"Variable: {key}, Description: {variable.description}, Dimensions: {','.join(variable.dimensions)}, Type: {variable.var_type}"
        )

    zarr_asset = collection.get_assets()["data"]
    water_bodies = xr.open_zarr(zarr_asset.get_absolute_href(), consolidated=True)

    logger.info(f"EPSG code: {str(water_bodies.data_vars['spatial_ref'].values)}")

    agg = water_bodies.mean(dim="time").to_array("data")

    agg = agg.rio.write_crs(f"EPSG:{str(water_bodies.data_vars['spatial_ref'].values)}")

    agg.rio.to_raster("water_bodies_mean.tif")

    logger.info(f"Creating a STAC Catalog for the output")
    cat = pystac.Catalog(id="catalog", description="water-bodies-mean")

    tmax = water_bodies.time.values.max()

    item_id = "occurrence"
    os.makedirs(item_id, exist_ok=True)
    shutil.copy("water_bodies_mean.tif", item_id)

    out_item = rio_stac.stac.create_stac_item(
        source="water_bodies_mean.tif",
        input_datetime=pd.to_datetime(tmax).to_pydatetime(),
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
