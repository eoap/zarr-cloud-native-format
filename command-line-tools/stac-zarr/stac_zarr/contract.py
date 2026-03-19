from datetime import datetime
from typing import List

from pystac import Collection, Item


def extract_crs(item: Item) -> str:
    """Extract CRS from a STAC item."""
    epsg = item.properties.get("proj:epsg")
    if epsg:
        return f"epsg:{epsg}"
    code = item.properties.get("proj:code")
    if code and code.upper().startswith("EPSG:"):
        return code.lower()
    raise ValueError("CRS not found in item properties")


def get_temporal_extent(items: List[Item]) -> List[datetime]:
    """Get temporal extent from a list of STAC items."""
    times = [item.datetime for item in items]
    if not times:
        raise ValueError("No datetime found in item properties")
    return [min(times), max(times)]


def get_spatial_extent(items: List[Item]) -> List[float]:
    """Get spatial extent from a list of STAC items."""
    bboxes = [item.bbox for item in items if item.bbox]
    if not bboxes:
        raise ValueError("No bbox found in item properties")
    min_x = min(bbox[0] for bbox in bboxes)
    min_y = min(bbox[1] for bbox in bboxes)
    max_x = max(bbox[2] for bbox in bboxes)
    max_y = max(bbox[3] for bbox in bboxes)
    return [min_x, min_y, max_x, max_y]


def get_measurement_keys(collection: Collection) -> List[str]:
    """Get measurement keys declared in Collection Item Assets."""
    if not collection.item_assets:
        raise ValueError(
            "Input STAC Collection must define item_assets. "
            "The tool uses collection.item_assets as the measurement contract."
        )
    measurement_keys = list(collection.item_assets.keys())
    if not measurement_keys:
        raise ValueError(
            "Input STAC Collection item_assets is empty. "
            "Define at least one measurement in collection.item_assets."
        )
    return measurement_keys


def validate_items_have_measurements(items: List[Item], measurement_keys: List[str]) -> None:
    """Ensure each item includes all measurements declared in collection.item_assets."""
    missing_by_item = {}
    for item in items:
        missing = [key for key in measurement_keys if key not in item.assets]
        if missing:
            missing_by_item[item.id] = missing
    if missing_by_item:
        details = "; ".join(
            f"{item_id}: {', '.join(missing)}"
            for item_id, missing in missing_by_item.items()
        )
        raise ValueError(
            "Input STAC Items are missing required Item Assets declared in "
            f"collection.item_assets: {details}"
        )
