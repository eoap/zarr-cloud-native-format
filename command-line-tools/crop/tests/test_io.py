from datetime import datetime, timezone

from pystac import Asset, Item

from crop_tool.io import aoi_to_box, get_asset_by_common_name


def _make_item_with_assets() -> Item:
    item = Item(
        id="test-item",
        geometry={"type": "Point", "coordinates": [0.0, 0.0]},
        bbox=[0.0, 0.0, 0.0, 0.0],
        datetime=datetime(2021, 1, 1, tzinfo=timezone.utc),
        properties={},
    )
    item.add_asset(
        "green",
        Asset(
            href="https://example.org/green.tif",
            roles=["data"],
            extra_fields={"eo:bands": [{"common_name": "green"}]},
        ),
    )
    item.add_asset(
        "thumbnail",
        Asset(
            href="https://example.org/thumbnail.jpg",
            roles=["thumbnail"],
            extra_fields={"eo:bands": [{"common_name": "green"}]},
        ),
    )
    return item


def test_aoi_to_box():
    assert aoi_to_box("1,2,3,4") == [1.0, 2.0, 3.0, 4.0]


def test_get_asset_by_common_name_selects_data_asset():
    item = _make_item_with_assets()
    asset = get_asset_by_common_name(item, "green")
    assert asset is not None
    assert asset.href.endswith("green.tif")


def test_get_asset_by_common_name_returns_none_when_missing():
    item = _make_item_with_assets()
    assert get_asset_by_common_name(item, "nir") is None
