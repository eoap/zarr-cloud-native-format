"""Exercise occurrence georeferencing without importing rioxarray in the test."""
import numpy as np
import xarray as xr
from pystac import Asset
from occurrence.app import attach_geobox_to_xarray


def test_measurement_projection_survives_raster_export(tmp_path):
    asset = Asset(href="measurements.zarr", extra_fields={
        "proj:code": "EPSG:32610",
        "proj:shape": [2, 3],
        "proj:bbox": [636990, 4410550, 637020, 4410570],
    })
    data = xr.DataArray(np.ones((2, 3)), dims=("y", "x"))
    result = attach_geobox_to_xarray(data, asset)
    assert result.rio.crs.to_epsg() == 32610
    assert tuple(result.rio.transform())[:6] == (10, 0, 636990, 0, -10, 4410570)
    destination = tmp_path / "occurrence.tif"
    result.rio.to_raster(destination)
    import rasterio
    with rasterio.open(destination) as raster:
        assert raster.crs.to_epsg() == 32610
        assert raster.shape == (2, 3)
        np.testing.assert_array_equal(raster.read(1), np.ones((2, 3)))
