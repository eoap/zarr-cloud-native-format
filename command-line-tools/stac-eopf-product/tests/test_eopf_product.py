from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from pystac import Asset, Catalog, Collection, Extent, Item, SpatialExtent, TemporalExtent
from pystac.extensions.raster import DataType
from xarray import DataArray

from stac_eopf_product.app import (
    build_stac_load_kwargs,
    extract_crs,
    get_measurement_keys,
    get_spatial_extent,
    get_temporal_extent,
    to_raster_datatype,
    validate_items_have_measurements,
)
from stac_eopf_product.writer import run_to_eopf


def _make_item(item_id: str, bbox, dt: datetime, properties=None) -> Item:
    if properties is None:
        properties = {}
    return Item(
        id=item_id,
        geometry={
            "type": "Polygon",
            "coordinates": [[[bbox[0], bbox[1]], [bbox[0], bbox[3]], [bbox[2], bbox[3]], [bbox[2], bbox[1]], [bbox[0], bbox[1]]]],
        },
        bbox=bbox,
        datetime=dt,
        properties=properties,
    )


def test_extract_crs_prefers_proj_epsg():
    item = _make_item(
        "a",
        [0, 0, 1, 1],
        datetime(2021, 1, 1, tzinfo=timezone.utc),
        properties={"proj:epsg": 32610, "proj:code": "EPSG:9999"},
    )
    assert extract_crs(item) == "epsg:32610"


def test_extract_crs_uses_proj_code():
    item = _make_item(
        "a",
        [0, 0, 1, 1],
        datetime(2021, 1, 1, tzinfo=timezone.utc),
        properties={"proj:code": "EPSG:32633"},
    )
    assert extract_crs(item) == "epsg:32633"


def test_get_extents():
    items = [
        _make_item("a", [1, 2, 3, 4], datetime(2021, 1, 2, tzinfo=timezone.utc)),
        _make_item("b", [-1, 0, 2, 8], datetime(2021, 1, 1, tzinfo=timezone.utc)),
    ]
    assert get_spatial_extent(items) == [-1, 0, 3, 8]
    start, end = get_temporal_extent(items)
    assert start.isoformat() == "2021-01-01T00:00:00+00:00"
    assert end.isoformat() == "2021-01-02T00:00:00+00:00"


def test_build_stac_load_kwargs_manual_chunks_and_resolution():
    kwargs = build_stac_load_kwargs(
        bands=["a", "b"],
        crs="epsg:32633",
        resolution=20.0,
        chunks="manual",
        chunk_x=256,
        chunk_y=128,
        chunk_time=2,
    )
    assert kwargs["bands"] == ["a", "b"]
    assert kwargs["crs"] == "epsg:32633"
    assert kwargs["groupby"] == "time"
    assert kwargs["resolution"] == 20.0
    assert kwargs["chunks"] == {"x": 256, "y": 128, "time": 2}


def test_build_stac_load_kwargs_auto_chunks_no_resolution():
    kwargs = build_stac_load_kwargs(
        bands=["a"],
        crs="epsg:32633",
        resolution=None,
        chunks="auto",
        chunk_x=256,
        chunk_y=128,
        chunk_time=2,
    )
    assert kwargs["bands"] == ["a"]
    assert kwargs["crs"] == "epsg:32633"
    assert kwargs["groupby"] == "time"
    assert "chunks" not in kwargs
    assert "resolution" not in kwargs


def test_to_raster_datatype():
    da = DataArray(np.array([1], dtype=np.uint8), dims=["x"])
    assert to_raster_datatype(da.dtype) == DataType.UINT8
    assert to_raster_datatype(np.dtype("complex64")) == DataType.OTHER


def test_get_measurement_keys_requires_item_assets():
    collection = SimpleNamespace(item_assets=None)
    with pytest.raises(ValueError, match="must define item_assets"):
        get_measurement_keys(collection)


def test_validate_items_have_measurements_reports_missing():
    items = [
        _make_item("a", [0, 0, 1, 1], datetime(2021, 1, 1, tzinfo=timezone.utc), properties={}),
        _make_item("b", [0, 0, 1, 1], datetime(2021, 1, 1, tzinfo=timezone.utc), properties={}),
    ]
    items[0].add_asset("water", Asset(href="file:///tmp/water_a.tif"))
    items[1].add_asset("water", Asset(href="file:///tmp/water_b.tif"))
    items[1].add_asset("ndwi", Asset(href="file:///tmp/ndwi_b.tif"))

    with pytest.raises(ValueError, match="a: ndwi"):
        validate_items_have_measurements(items, ["water", "ndwi"])


def test_run_to_eopf_uses_collection_measurements_and_load_kwargs(monkeypatch, tmp_path: Path):
    collection = Collection(
        id="demo",
        description="Demo collection",
        title="Demo",
        extent=Extent(
            spatial=SpatialExtent([[-1.0, -1.0, 1.0, 1.0]]),
            temporal=TemporalExtent([[None, None]]),
        ),
    )
    collection.item_assets = {
        "water": {"title": "Water", "description": "Detected water"},
        "ndwi": {"title": "NDWI", "description": "NDWI index"},
    }

    item = _make_item(
        "item-1",
        [10.0, 20.0, 11.0, 21.0],
        datetime(2021, 1, 1, tzinfo=timezone.utc),
        properties={"proj:epsg": 32633},
    )
    item.add_asset("water", Asset(href="file:///tmp/water.tif"))
    item.add_asset("ndwi", Asset(href="file:///tmp/ndwi.tif"))
    collection.add_item(item)

    catalog = Catalog(id="root", description="root")
    catalog.add_child(collection)

    class FakeExtent:
        def to_crs(self, _crs):
            return self

        @property
        def json(self):
            return {"type": "Polygon", "coordinates": []}

    class FakeGeoBox:
        crs = SimpleNamespace(epsg=32633)
        extent = FakeExtent()
        shape = (2, 3)

    class FakeDataset:
        def __init__(self):
            self.x = SimpleNamespace(values=np.array([100.0, 110.0, 120.0]))
            self.y = SimpleNamespace(values=np.array([200.0, 190.0]))
            self.odc = SimpleNamespace(geobox=FakeGeoBox())
            self.data = {
                "water": DataArray(np.ones((1, 2, 3), dtype=np.uint8), dims=["time", "y", "x"]),
                "ndwi": DataArray(np.ones((1, 2, 3), dtype=np.float32), dims=["time", "y", "x"]),
            }

        def __getitem__(self, key):
            return self.data[key]

    captured = {}

    def fake_stac_load(items, **kwargs):
        captured["item_count"] = len(items)
        captured["kwargs"] = kwargs
        return FakeDataset()

    class FakeEOProduct(dict):
        pass

    class FakeEOGroup(dict):
        pass

    class FakeEOVariable:
        def __init__(self, data, dims, attrs):
            self.data = data
            self.dims = dims
            self.attrs = attrs

    class FakeEOZarrStore:
        last_key = None
        last_url = None

        def __init__(self, url):
            self.url = url

        def open(self, mode):
            return self

        def __enter__(self):
            FakeEOZarrStore.last_url = self.url
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __setitem__(self, key, value):
            FakeEOZarrStore.last_key = key

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("stac_eopf_product.writer.read_stac_file", lambda _p: catalog)
    monkeypatch.setattr("stac_eopf_product.writer.stac_load", fake_stac_load)
    monkeypatch.setattr("stac_eopf_product.writer.EOProduct", FakeEOProduct)
    monkeypatch.setattr("stac_eopf_product.writer.EOGroup", FakeEOGroup)
    monkeypatch.setattr("stac_eopf_product.writer.EOVariable", FakeEOVariable)
    monkeypatch.setattr("stac_eopf_product.writer.EOZarrStore", FakeEOZarrStore)

    run_to_eopf(
        stac_catalog=tmp_path,
        resolution=20.0,
        chunks="manual",
        chunk_x=128,
        chunk_y=64,
        chunk_time=1,
    )

    assert captured["item_count"] == 1
    assert captured["kwargs"]["bands"] == ["water", "ndwi"]
    assert captured["kwargs"]["resolution"] == 20.0
    assert captured["kwargs"]["chunks"] == {"x": 128, "y": 64, "time": 1}
    assert FakeEOZarrStore.last_key == "demo"
    assert FakeEOZarrStore.last_url.startswith("file://")
