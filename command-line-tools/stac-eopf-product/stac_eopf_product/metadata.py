from datetime import datetime
from typing import List, Tuple

from pystac import Collection, Extent, SpatialExtent, TemporalExtent
from xarray import Dataset


def build_output_collection(
    input_collection: Collection,
    spatial_extent: List[float],
    temporal_extent: List[datetime],
) -> Collection:
    return Collection(
        id=input_collection.id,
        description=input_collection.description,
        title=input_collection.title,
        extent=Extent(
            spatial=SpatialExtent(bboxes=[spatial_extent]),
            temporal=TemporalExtent([temporal_extent]),
        ),
    )


def get_measurement_text(collection: Collection, measurement: str) -> Tuple[str, str]:
    item_asset = collection.item_assets.get(measurement) if collection.item_assets else None
    if isinstance(item_asset, dict):
        title = item_asset.get("title") or measurement
        description = item_asset.get("description") or measurement
        return title, description

    title = item_asset.title if item_asset and getattr(item_asset, "title", None) else measurement
    description = (
        item_asset.description
        if item_asset and getattr(item_asset, "description", None)
        else measurement
    )
    return title, description


def build_cube_dimensions(dataset: Dataset, temporal_extent: List[datetime]) -> dict:
    return {
        "time": {
            "type": "temporal",
            "extent": [
                temporal_extent[0].isoformat() + "Z",
                temporal_extent[1].isoformat() + "Z",
            ],
        },
        "x": {
            "type": "spatial",
            "axis": "x",
            "extent": [
                float(min(dataset.x.values)),
                float(max(dataset.x.values)),
            ],
        },
        "y": {
            "type": "spatial",
            "axis": "y",
            "extent": [
                float(min(dataset.y.values)),
                float(max(dataset.y.values)),
            ],
        },
    }
