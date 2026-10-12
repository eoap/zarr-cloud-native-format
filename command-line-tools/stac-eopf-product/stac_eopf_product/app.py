from stac_eopf_product.cli import to_eopf
from stac_eopf_product.contract import extract_crs as extract_crs
from stac_eopf_product.contract import get_asset_keys as get_asset_keys
from stac_eopf_product.contract import get_measurement_keys as get_measurement_keys
from stac_eopf_product.contract import get_spatial_extent as get_spatial_extent
from stac_eopf_product.contract import get_temporal_extent as get_temporal_extent
from stac_eopf_product.contract import (
    validate_items_have_measurements as validate_items_have_measurements,
)
from stac_eopf_product.writer import build_stac_load_kwargs as build_stac_load_kwargs
from stac_eopf_product.writer import raster_band_from_dataarray as raster_band_from_dataarray
from stac_eopf_product.writer import run_to_eopf as run_to_eopf
from stac_eopf_product.writer import to_raster_datatype as to_raster_datatype

if __name__ == "__main__":
    to_eopf()
