import rasterio
from loguru import logger
from pyproj import Transformer
from rasterio.mask import mask
from shapely import box

from crop_tool.io import aoi_to_box, get_asset_by_common_name, read_input_item
from crop_tool.signing import item_requires_mspc_signing, sign_item_for_mspc


def run_crop(item_url: str, aoi: str, band: str, epsg: str, asset_signing: str = "auto") -> None:
    """Crop STAC item asset and write a local COG file."""
    item = read_input_item(item_url)

    signing_mode = asset_signing.lower()
    should_sign_mspc = signing_mode == "mspc" or (
        signing_mode == "auto" and item_requires_mspc_signing(item)
    )
    if should_sign_mspc:
        logger.info("Signing item asset HREFs for Microsoft Planetary Computer...")
        item = sign_item_for_mspc(item)

    logger.info(f"Read {item.id} from {item.get_self_href()}")

    asset = get_asset_by_common_name(item, band)
    if asset is None:
        msg = f"Common band name {band} not found in the assets"
        logger.error(msg)
        raise ValueError(msg)
    logger.info(f"Read asset {band} from {asset.get_absolute_href()}")

    bbox = aoi_to_box(aoi)

    with rasterio.open(asset.get_absolute_href()) as src:
        transformer = Transformer.from_crs(epsg, src.crs, always_xy=True)

        minx, miny = transformer.transform(bbox[0], bbox[1])
        maxx, maxy = transformer.transform(bbox[2], bbox[3])
        transformed_bbox = box(minx, miny, maxx, maxy)

        logger.info(f"Crop {asset.get_absolute_href()}")

        out_image, out_transform = mask(src, [transformed_bbox], crop=True)
        out_meta = src.meta.copy()
        out_meta.update(
            {
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "dtype": "uint16",
                "driver": "COG",
                "tiled": True,
                "compress": "lzw",
                "blockxsize": 256,
                "blockysize": 256,
            }
        )

        output_path = f"crop_{band}.tif"
        with rasterio.open(output_path, "w", **out_meta) as dst_dataset:
            logger.info(f"Write {output_path}")
            dst_dataset.write(out_image)

    logger.info("Done!")
