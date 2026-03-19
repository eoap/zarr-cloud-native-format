from stac_eopf_product.cli import to_eopf
from stac_eopf_product.contract import (
    extract_crs,
    get_asset_keys,
    get_measurement_keys,
    get_spatial_extent,
    get_temporal_extent,
    validate_items_have_measurements,
)
from stac_eopf_product.writer import build_stac_load_kwargs, raster_band_from_dataarray, run_to_eopf, to_raster_datatype


if __name__ == "__main__":
    to_eopf()
