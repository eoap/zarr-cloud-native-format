import os

import pystac
from pystac import Asset, Item


def aoi_to_box(aoi: str) -> list[float]:
    """Convert CSV bbox string into a float list."""
    return [float(c) for c in aoi.split(",")]


def read_input_item(item_url: str) -> Item:
    """Read input STAC item from an item URL or staged catalog directory."""
    if os.path.isdir(item_url):
        catalog = pystac.read_file(os.path.join(item_url, "catalog.json"))
        return next(catalog.get_items())
    return pystac.read_file(item_url)


def get_asset_by_common_name(item: Item, common_name: str) -> Asset | None:
    """Return STAC Item asset matching the EO common band name."""
    for _, asset in item.get_assets().items():
        roles = asset.to_dict().get("roles", [])
        if "data" not in roles:
            continue

        eo_asset = pystac.extensions.eo.AssetEOExtension(asset)
        if not eo_asset.bands:
            continue
        for band in eo_asset.bands:
            if band.properties.get("common_name") == common_name:
                return asset
    return None
