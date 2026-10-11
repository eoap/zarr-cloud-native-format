from datetime import datetime, timezone

from pystac import Asset, Item

from crop_tool.signing import asset_href_needs_mspc_signing, item_requires_mspc_signing


def _make_item(asset_href: str) -> Item:
    item = Item(
        id="test-item",
        geometry={"type": "Point", "coordinates": [0.0, 0.0]},
        bbox=[0.0, 0.0, 0.0, 0.0],
        datetime=datetime(2021, 1, 1, tzinfo=timezone.utc),
        properties={},
    )
    item.add_asset("band", Asset(href=asset_href, roles=["data"]))
    return item


def test_asset_href_needs_mspc_signing_true_for_unsigned_blob_href():
    href = "https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/abc.tif"
    assert asset_href_needs_mspc_signing(href) is True


def test_asset_href_needs_mspc_signing_false_for_signed_blob_href():
    href = "https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/abc.tif?st=a&se=b&sp=rl"
    assert asset_href_needs_mspc_signing(href) is False


def test_asset_href_needs_mspc_signing_false_for_public_ai4e_account():
    href = "https://ai4edatasetspublicassets.blob.core.windows.net/public/abc.tif"
    assert asset_href_needs_mspc_signing(href) is False


def test_item_requires_mspc_signing_true_when_any_asset_needs_signing():
    item = _make_item("https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/abc.tif")
    assert item_requires_mspc_signing(item) is True


def test_item_requires_mspc_signing_false_when_assets_do_not_need_signing():
    item = _make_item("https://example.org/data/abc.tif")
    assert item_requires_mspc_signing(item) is False
