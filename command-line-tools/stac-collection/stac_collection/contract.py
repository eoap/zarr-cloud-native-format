from datetime import datetime
from typing import List

from pystac import Item


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


def validate_parallel_inputs(item_urls: tuple[str, ...], otsu: tuple[str, ...], ndwi: tuple[str, ...]) -> None:
    """Ensure all repeated CLI inputs have the same number of entries."""
    if not (len(item_urls) == len(otsu) == len(ndwi)):
        raise ValueError(
            "Input lengths must match: "
            f"--input-item={len(item_urls)}, --otsu={len(otsu)}, --ndwi={len(ndwi)}"
        )
