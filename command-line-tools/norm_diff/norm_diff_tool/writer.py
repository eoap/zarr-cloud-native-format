import rasterio
from loguru import logger

from norm_diff_tool.compute import normalized_difference


def run_norm_diff(raster_a: str, raster_b: str, output_path: str = "norm_diff.tif") -> None:
    """Compute normalized difference from two raster files."""
    logger.info(f"Processing the normalized image with {raster_a} and {raster_b}")

    with rasterio.open(raster_a) as ds1:
        array1 = ds1.read(1).astype("float32")
        out_meta = ds1.meta.copy()

    with rasterio.open(raster_b) as ds2:
        array2 = ds2.read(1).astype("float32")

    out_meta.update(
        {
            "dtype": "float32",
            "driver": "COG",
            "tiled": True,
            "compress": "lzw",
            "blockxsize": 256,
            "blockysize": 256,
        }
    )

    with rasterio.open(output_path, "w", **out_meta) as dst_dataset:
        logger.info(f"Write {output_path}")
        dst_dataset.write(normalized_difference(array1, array2), 1)

    logger.info("Done!")

