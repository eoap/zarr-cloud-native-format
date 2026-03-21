import rasterio
from loguru import logger

from otsu_tool.threshold import threshold


def run_otsu(raster: str, output_path: str = "otsu.tif") -> None:
    """Apply Otsu thresholding and write a binary COG output."""
    with rasterio.open(raster) as ds:
        array = ds.read(1)
        out_meta = ds.meta.copy()

    out_meta.update(
        {
            "dtype": "uint8",
            "driver": "COG",
            "tiled": True,
            "compress": "lzw",
            "blockxsize": 256,
            "blockysize": 256,
        }
    )

    logger.info(f"Applying the Otsu threshold to {raster}")

    with rasterio.open(output_path, "w", **out_meta) as dst_dataset:
        logger.info(f"Write {output_path}")
        dst_dataset.write(threshold(array), indexes=1)

    logger.info("Done!")
