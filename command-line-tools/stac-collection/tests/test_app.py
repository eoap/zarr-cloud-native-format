from datetime import datetime, timezone
from pathlib import Path

import pytest
from pystac import Asset, Catalog, Extent, Item, SpatialExtent, TemporalExtent, read_file

from stac_collection.app import (
    get_spatial_extent,
    get_temporal_extent,
    run_to_stac,
    validate_parallel_inputs,
)


def _make_item(item_id: str, dt: datetime, bbox):
    return Item(
        id=item_id,
        geometry={
            "type": "Polygon",
            "coordinates": [[[bbox[0], bbox[1]], [bbox[0], bbox[3]], [bbox[2], bbox[3]], [bbox[2], bbox[1]], [bbox[0], bbox[1]]]],
        },
        bbox=bbox,
        datetime=dt,
        properties={},
    )


def test_get_temporal_extent():
    items = [
        _make_item("a", datetime(2021, 1, 2, tzinfo=timezone.utc), [0, 0, 1, 1]),
        _make_item("b", datetime(2021, 1, 1, tzinfo=timezone.utc), [0, 0, 1, 1]),
    ]
    start, end = get_temporal_extent(items)
    assert start.isoformat() == "2021-01-01T00:00:00+00:00"
    assert end.isoformat() == "2021-01-02T00:00:00+00:00"


def test_get_spatial_extent():
    items = [
        _make_item("a", datetime(2021, 1, 1, tzinfo=timezone.utc), [1, 2, 3, 4]),
        _make_item("b", datetime(2021, 1, 2, tzinfo=timezone.utc), [-1, 0, 2, 8]),
    ]
    assert get_spatial_extent(items) == [-1, 0, 3, 8]


def test_validate_parallel_inputs_mismatch():
    with pytest.raises(ValueError, match="Input lengths must match"):
        validate_parallel_inputs(("a",), ("b", "c"), ("d",))


def test_run_to_stac_builds_catalog(monkeypatch, tmp_path):
    item = _make_item(
        "S2A_TEST",
        datetime(2021, 6, 28, tzinfo=timezone.utc),
        [1.0, 2.0, 3.0, 4.0],
    )
    item_path = tmp_path / "item.json"
    item.save_object(dest_href=str(item_path))

    otsu_path = tmp_path / "mask.tif"
    ndwi_path = tmp_path / "ndwi.tif"
    otsu_path.write_text("dummy")
    ndwi_path.write_text("dummy")

    def fake_create_stac_item(
        source,
        input_datetime,
        id,
        asset_roles,
        asset_href,
        asset_name,
        with_proj,
        with_raster,
    ):
        out = _make_item(id, input_datetime, [1.0, 2.0, 3.0, 4.0])
        out.add_asset(asset_name, Asset(href=asset_href, roles=asset_roles))
        return out

    import rio_stac

    monkeypatch.setattr(rio_stac.stac, "create_stac_item", fake_create_stac_item)

    output_dir = tmp_path / "out"
    run_to_stac(
        item_urls=(str(item_path),),
        otsu=(str(otsu_path),),
        ndwi=(str(ndwi_path),),
        output_dir=output_dir,
    )

    catalog = read_file(str(output_dir / "catalog.json"))
    assert isinstance(catalog, Catalog)
    collection = next(catalog.get_children())
    assert collection.id == "water-bodies"
    assert "water-bodies" in collection.item_assets
    assert "ndwi" in collection.item_assets
    out_item = next(collection.get_items())
    assert "water-bodies" in out_item.assets
    assert "ndwi" in out_item.assets
