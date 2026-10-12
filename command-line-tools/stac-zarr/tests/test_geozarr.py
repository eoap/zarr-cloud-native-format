"""Exercise the production writer and reject corrupted stores with GeoZarr Toolkit."""

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import zarr
from affine import Affine
from click.testing import CliRunner
from geozarr_toolkit import validate_attrs
from odc.geo.geobox import GeoBox
from odc.geo.xr import xr_zeros
from pystac import (
    Asset,
    Catalog,
    Collection,
    Extent,
    Item,
    SpatialExtent,
    TemporalExtent,
)

from stac_zarr import validate_geozarr_store, writer
from stac_zarr.cli import validate_store


@pytest.fixture
def generated_store(tmp_path, monkeypatch):
    catalog = Catalog("input", "input")
    collection = Collection(
        "sample",
        "sample",
        Extent(SpatialExtent([[0, 0, 1, 1]]), TemporalExtent([[None, None]])),
    )
    collection.extra_fields["item_assets"] = {"water": {"type": "image/tiff", "title": "Water"}}
    item = Item(
        "scene",
        None,
        [0, 0, 1, 1],
        datetime(2026, 1, 1, tzinfo=UTC),
        {"proj:code": "EPSG:32633"},
    )
    item.add_asset("water", Asset("unused.tif"))
    collection.add_item(item)
    catalog.add_child(collection)
    geobox = GeoBox((8, 8), Affine(10, 0, 300000, 0, -10, 5000000), "EPSG:32633")
    da = (
        xr_zeros(geobox, dtype="uint8")
        .expand_dims(time=[np.datetime64("2026-01-01")])
        .chunk({"time": 1, "y": 4, "x": 4})
    )
    monkeypatch.setattr(writer, "read_stac_file", lambda _: catalog)
    monkeypatch.setattr(writer, "stac_load", lambda *args, **kwargs: da.to_dataset(name="water"))
    monkeypatch.chdir(tmp_path)
    validation = Mock(wraps=writer.validate_geozarr_store)
    monkeypatch.setattr(writer, "validate_geozarr_store", validation)
    writer.run_to_zarr(tmp_path, 2, "mean", "nearest")
    validation.assert_called_once()
    return zarr.open_group(tmp_path / "sample/sample.zarr", mode="r+", use_consolidated=False)


def test_writer_store_passes_toolkit(generated_store):
    root = generated_store
    validate_geozarr_store(root)
    assert root.attrs["spatial:bbox"] == [300000, 4999920, 300080, 5000000]
    assert {e["name"] for e in root.attrs["zarr_conventions"]} == {
        "proj",
        "spatial",
        "multiscales",
    }
    for path in [
        "measurements/water",
        "measurements_overviews/water/1/water",
        "measurements_overviews/water/2/water",
    ]:
        array = root[path]
        assert all(not errors for errors in validate_attrs(dict(array.attrs)).values())
        assert any(key.startswith("proj:") for key in array.attrs)
        for key, value in root.attrs.items():
            if key.startswith("proj:"):
                assert array.attrs[key] == value
        assert array.attrs["spatial:shape"] == list(array.shape[-2:])
        assert array.metadata.dimension_names == ("time", "y", "x")


def test_store_validation_command(generated_store):
    script = Path(__file__).resolve().parents[3] / "scripts/validate_geozarr_store.py"
    store = generated_store.store.root
    result = subprocess.run(
        [sys.executable, str(script), str(store)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    generated_store["measurements/water"].attrs["spatial:shape"] = [99, 99]
    result = subprocess.run(
        [sys.executable, str(script), str(store)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "FAIL" in result.stderr
    assert "disagrees with array shape" in result.stderr


def test_module_api_and_cli(generated_store):
    path = Path(generated_store.store.root)
    validate_geozarr_store(path)
    validate_geozarr_store(str(path))
    runner = CliRunner()
    result = runner.invoke(validate_store, [str(path)])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output
    generated_store["measurements/water"].attrs["spatial:shape"] = [99, 99]
    with pytest.raises(ValueError, match="disagrees with array shape"):
        validate_geozarr_store(path)
    result = runner.invoke(validate_store, [str(path)])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def _remove_projection(array):
    for key in list(array.attrs):
        if key.startswith("proj:"):
            del array.attrs[key]


def _corrupt_multiscales(root, corruption):
    metadata = dict(root.attrs["multiscales"])
    if corruption == "path":
        metadata["layout"][0]["asset"] = "missing/water"
    else:
        metadata["layout"][0]["spatial:transform"] = [1, 0, 0, 0, -1, 0]
    root.attrs["multiscales"] = metadata


@pytest.mark.parametrize(
    "corruption, message",
    [
        ("declaration", "incorrect schema_url"),
        ("transform", "spatial"),
        ("shape", "disagrees with array shape"),
        ("dimensions", "dimension_names"),
        ("projection", "proj"),
        ("missing_metadata", "missing array projection"),
        ("path", "multiscales asset missing"),
        ("layout", "layout spatial:transform disagrees"),
    ],
)
def test_rejects_corrupted_store(generated_store, corruption, message):
    root = generated_store
    array = root["measurements_overviews/water/2/water"]
    if corruption == "declaration":
        entries = list(array.attrs["zarr_conventions"])
        entries[0]["schema_url"] = entries[0]["schema_url"].replace("v0.1", "v1")
        array.attrs["zarr_conventions"] = entries
    elif corruption == "transform":
        array.attrs["spatial:transform"] = [1, 2]
    elif corruption == "shape":
        array.attrs["spatial:shape"] = [99, 99]
    elif corruption == "dimensions":
        array.attrs["spatial:dimensions"] = ["lat", "lon"]
    elif corruption == "projection":
        _remove_projection(array)
    elif corruption == "missing_metadata":
        for key in list(array.attrs):
            if key.startswith(("proj:", "spatial:")) or key == "zarr_conventions":
                del array.attrs[key]
    else:
        _corrupt_multiscales(root, corruption)
    with pytest.raises(ValueError, match=message):
        validate_geozarr_store(root)
