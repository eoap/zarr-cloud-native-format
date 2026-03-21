from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pytest
import zarr
from click.testing import CliRunner
from pystac import Asset, Collection, Extent, Item, SpatialExtent, TemporalExtent
from xarray import DataArray, Dataset

from stac_zarr.app import (
    _write_cf_dataset_members,
    build_root_proj_metadata,
    build_tile_matrix_limits,
    build_tile_matrix_set,
    check_grid_mapping,
    check_valid_coordinates,
    downsample_2x,
    get_measurement_keys,
    get_variable_type,
    to_resampling_method,
    validate_items_have_measurements,
)
from stac_zarr.writer import (
    consolidate_zarr_store,
    ensure_unique_time_index,
    format_time_values_for_summaries,
    normalize_renders_for_zarr,
    to_pystac_renders,
)
import stac_zarr.cli as cli_mod
from stac_zarr.multiscales import build_v1_layout


def _make_collection(item_assets):
    collection = Collection(
        id="c",
        description="d",
        extent=Extent(
            spatial=SpatialExtent([[-10.0, -10.0, 10.0, 10.0]]),
            temporal=TemporalExtent([[None, None]]),
        ),
    )
    collection.item_assets = item_assets
    return collection


def _make_item(item_id: str, asset_names):
    item = Item(
        id=item_id,
        geometry={
            "type": "Polygon",
            "coordinates": [[[-1.0, -1.0], [-1.0, 1.0], [1.0, 1.0], [1.0, -1.0], [-1.0, -1.0]]],
        },
        bbox=[-1.0, -1.0, 1.0, 1.0],
        datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
        properties={},
    )
    for name in asset_names:
        item.add_asset(name, Asset(href=f"s3://example/{name}.tif"))
    return item


def test_to_resampling_method_mapping():
    assert to_resampling_method("mean") == "average"
    assert to_resampling_method("nearest") == "nearest"
    assert to_resampling_method("max") == "max"
    assert to_resampling_method("median") == "med"


def test_build_tile_matrix_set():
    tms = build_tile_matrix_set(
        proj_code="EPSG:32633",
        affine_6=[10.0, 0.0, 300000.0, 0.0, -10.0, 5000000.0],
        base_shape=[[1094, 1094], [547, 547], [273, 273]],
        chunk_shape=[512, 512],
    )

    assert tms["id"] == "EPSG_32633_multiscale"
    assert tms["crs"] == "EPSG:32633"
    assert [m["id"] for m in tms["tileMatrices"]] == ["0", "1", "2"]
    assert tms["tileMatrices"][0]["cellSize"] == 10.0
    assert tms["tileMatrices"][1]["cellSize"] == 20.0
    assert tms["tileMatrices"][0]["tileWidth"] == 512
    assert tms["tileMatrices"][0]["matrixWidth"] == 3
    assert tms["tileMatrices"][0]["matrixHeight"] == 3
    assert tms["tileMatrices"][1]["matrixWidth"] == 2
    assert tms["tileMatrices"][1]["matrixHeight"] == 2


def test_build_tile_matrix_limits():
    tms = build_tile_matrix_set(
        proj_code="EPSG:32633",
        affine_6=[10.0, 0.0, 300000.0, 0.0, -10.0, 5000000.0],
        base_shape=[[1094, 1094], [547, 547], [273, 273]],
        chunk_shape=[512, 512],
    )
    limits = build_tile_matrix_limits(tms)

    assert [entry["tileMatrix"] for entry in limits] == ["0", "1", "2"]
    assert limits[0] == {
        "tileMatrix": "0",
        "minTileRow": 0,
        "maxTileRow": 2,
        "minTileCol": 0,
        "maxTileCol": 2,
    }
    assert limits[1] == {
        "tileMatrix": "1",
        "minTileRow": 0,
        "maxTileRow": 1,
        "minTileCol": 0,
        "maxTileCol": 1,
    }


def test_build_v1_layout():
    entries = [
        {
            "name": "ndwi",
            "datasets": [
                {
                    "path": "measurements/ndwi",
                    "level": 0,
                    "spatial:shape": [1094, 1094],
                    "spatial:transform": [10.0, 0.0, 300000.0, 0.0, -10.0, 5000000.0],
                },
                {
                    "path": "measurements_overviews/ndwi/1/ndwi",
                    "level": 1,
                    "downsampling_factor": 2,
                    "overview:reducer": "mean",
                    "spatial:shape": [547, 547],
                    "spatial:transform": [20.0, 0.0, 300000.0, 0.0, -20.0, 5000000.0],
                },
                {
                    "path": "measurements_overviews/ndwi/2/ndwi",
                    "level": 2,
                    "downsampling_factor": 4,
                    "overview:reducer": "mean",
                    "spatial:shape": [274, 274],
                    "spatial:transform": [40.0, 0.0, 300000.0, 0.0, -40.0, 5000000.0],
                },
            ],
        }
    ]

    layout = build_v1_layout(entries)

    assert [entry["asset"] for entry in layout] == [
        "measurements/ndwi",
        "measurements_overviews/ndwi/1/ndwi",
        "measurements_overviews/ndwi/2/ndwi",
    ]
    assert "derived_from" not in layout[0]
    assert layout[1]["derived_from"] == "measurements/ndwi"
    assert layout[1]["transform"]["scale"] == [2.0, 2.0]
    assert layout[2]["derived_from"] == "measurements_overviews/ndwi/1/ndwi"
    assert layout[2]["transform"]["scale"] == [2.0, 2.0]


def test_build_root_proj_metadata_full():
    class FakeCRS:
        def to_wkt(self, _dialect):
            return "WKT2:FAKE"

        def to_json_dict(self):
            return {"type": "ProjectedCRS", "name": "fake"}

    meta = build_root_proj_metadata(FakeCRS(), "EPSG:32633")
    assert "proj:code" not in meta
    assert "proj:wkt2" not in meta
    assert meta["proj:projjson"]["type"] == "ProjectedCRS"


def test_build_root_proj_metadata_wkt_fallback():
    class FakeCRS:
        def to_wkt(self, _dialect):
            return "WKT2:FAKE"

    meta = build_root_proj_metadata(FakeCRS(), "EPSG:32633")
    assert meta == {"proj:wkt2": "WKT2:FAKE"}


def test_build_root_proj_metadata_fallback():
    class FakeCRS:
        def to_wkt(self, _dialect):
            raise RuntimeError("missing wkt")

    meta = build_root_proj_metadata(FakeCRS(), "EPSG:32633")
    assert meta == {"proj:code": "EPSG:32633"}


def test_write_cf_dataset_members(tmp_path):
    da = DataArray(
        np.arange(24, dtype=np.float32).reshape(2, 3, 4),
        dims=["time", "y", "x"],
        coords={
            "time": np.array(["2021-06-01T00:00:00", "2021-06-02T00:00:00"], dtype="datetime64[s]"),
            "y": np.array([1000.0, 990.0, 980.0], dtype=np.float64),
            "x": np.array([200.0, 210.0, 220.0, 230.0], dtype=np.float64),
        },
    )
    group = zarr.open_group(tmp_path / "cf-dataset.zarr", mode="w")
    _write_cf_dataset_members(
        dataset_group=group,
        da=da,
        transform_6=[10.0, 0.0, 195.0, 0.0, -10.0, 1005.0],
        crs_wkt="EPSG:32610-WKT",
    )

    assert "time" in group.array_keys()
    assert "y" in group.array_keys()
    assert "x" in group.array_keys()
    assert "spatial_ref" in group.array_keys()

    assert group["x"].attrs["standard_name"] == "projection_x_coordinate"
    assert group["y"].attrs["standard_name"] == "projection_y_coordinate"
    assert group["spatial_ref"].attrs["crs_wkt"] == "EPSG:32610-WKT"
    assert "GeoTransform" in group["spatial_ref"].attrs


def _make_data_array(group, name: str, grid_mapping: str = "spatial_ref"):
    arr = group.create(
        name=name,
        shape=(2, 3, 4),
        chunks=(1, 3, 4),
        dtype=np.float32,
        overwrite=True,
        dimension_names=["time", "y", "x"],
        attributes={"grid_mapping": grid_mapping, "coordinates": "time y x"},
    )
    arr[...] = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
    return arr


def test_check_valid_coordinates_and_grid_mapping_ok(tmp_path):
    da = DataArray(
        np.arange(24, dtype=np.float32).reshape(2, 3, 4),
        dims=["time", "y", "x"],
        coords={
            "time": np.array(["2021-06-01T00:00:00", "2021-06-02T00:00:00"], dtype="datetime64[s]"),
            "y": np.array([1000.0, 990.0, 980.0], dtype=np.float64),
            "x": np.array([200.0, 210.0, 220.0, 230.0], dtype=np.float64),
        },
    )
    group = zarr.open_group(tmp_path / "cf-validate-ok.zarr", mode="w")
    _write_cf_dataset_members(group, da, [10.0, 0.0, 195.0, 0.0, -10.0, 1005.0], "EPSG:32610-WKT")
    _make_data_array(group, "water")

    check_valid_coordinates(group)
    check_grid_mapping(group)


def test_check_valid_coordinates_fails_on_missing_dim(tmp_path):
    group = zarr.open_group(tmp_path / "cf-validate-missing-dim.zarr", mode="w")
    _make_data_array(group, "water")
    with pytest.raises(ValueError, match="Dimension 'time'.*not defined"):
        check_valid_coordinates(group)


def test_check_grid_mapping_fails_on_missing_member(tmp_path):
    da = DataArray(
        np.arange(24, dtype=np.float32).reshape(2, 3, 4),
        dims=["time", "y", "x"],
        coords={
            "time": np.array(["2021-06-01T00:00:00", "2021-06-02T00:00:00"], dtype="datetime64[s]"),
            "y": np.array([1000.0, 990.0, 980.0], dtype=np.float64),
            "x": np.array([200.0, 210.0, 220.0, 230.0], dtype=np.float64),
        },
    )
    group = zarr.open_group(tmp_path / "cf-validate-missing-gm.zarr", mode="w")
    _write_cf_dataset_members(group, da, [10.0, 0.0, 195.0, 0.0, -10.0, 1005.0], "EPSG:32610-WKT")
    _make_data_array(group, "water", grid_mapping="missing_spatial_ref")
    with pytest.raises(ValueError, match="missing_spatial_ref"):
        check_grid_mapping(group)


def test_get_measurement_keys_requires_item_assets():
    collection = SimpleNamespace(item_assets=None)
    with pytest.raises(ValueError, match="must define item_assets"):
        get_measurement_keys(collection)


def test_get_measurement_keys_requires_non_empty_item_assets():
    collection = SimpleNamespace(item_assets={})
    with pytest.raises(ValueError, match="must define item_assets"):
        get_measurement_keys(collection)


def test_validate_items_have_measurements_ok():
    items = [
        _make_item("a", ["water", "ndwi"]),
        _make_item("b", ["water", "ndwi"]),
    ]
    validate_items_have_measurements(items, ["water", "ndwi"])


def test_validate_items_have_measurements_reports_missing():
    items = [
        _make_item("a", ["water"]),
        _make_item("b", ["water", "ndwi"]),
    ]
    with pytest.raises(ValueError, match="a: ndwi"):
        validate_items_have_measurements(items, ["water", "ndwi"])


def test_get_variable_type():
    float_da = DataArray(np.array([1.0], dtype=np.float32), dims=["x"])
    int_da = DataArray(np.array([1], dtype=np.uint8), dims=["x"])
    assert get_variable_type(float_da) == "continuous"
    assert get_variable_type(int_da) == "categorical"


def test_downsample_2x_nearest():
    da = DataArray(np.arange(16, dtype=np.float32).reshape(1, 4, 4), dims=["time", "y", "x"])
    out = downsample_2x(da, "nearest")
    assert out.shape == (1, 2, 2)
    assert out.values.tolist() == [[[0.0, 2.0], [8.0, 10.0]]]


def test_downsample_2x_mean():
    da = DataArray(np.arange(16, dtype=np.float32).reshape(1, 4, 4), dims=["time", "y", "x"])
    out = downsample_2x(da, "mean")
    assert out.shape == (1, 2, 2)
    assert out.values.tolist() == [[[2.5, 4.5], [10.5, 12.5]]]


def test_downsample_2x_max():
    da = DataArray(np.arange(16, dtype=np.float32).reshape(1, 4, 4), dims=["time", "y", "x"])
    out = downsample_2x(da, "max")
    assert out.shape == (1, 2, 2)
    assert out.values.tolist() == [[[5.0, 7.0], [13.0, 15.0]]]


def test_downsample_2x_median():
    da = DataArray(np.arange(16, dtype=np.float32).reshape(1, 4, 4), dims=["time", "y", "x"])
    out = downsample_2x(da, "median")
    assert out.shape == (1, 2, 2)
    assert out.values.tolist() == [[[2.5, 4.5], [10.5, 12.5]]]


def test_downsample_2x_rejects_unknown_reducer():
    da = DataArray(np.arange(4, dtype=np.float32).reshape(1, 2, 2), dims=["time", "y", "x"])
    with pytest.raises(ValueError, match="Unsupported overview reducer"):
        downsample_2x(da, "p90")


def test_consolidate_zarr_store_writes_metadata(tmp_path):
    root = zarr.open_group(tmp_path / "sample.zarr", mode="w")
    root.create("a", shape=(2, 2), chunks=(1, 1), dtype=np.int16, overwrite=True)
    consolidate_zarr_store(tmp_path / "sample.zarr")
    reopened = zarr.open_group(tmp_path / "sample.zarr", mode="r")
    assert reopened.metadata.consolidated_metadata is not None
    assert "a" in reopened.metadata.consolidated_metadata.metadata


def test_cli_forwards_titiler_eopf_compatible_flag(tmp_path, monkeypatch):
    captured = {}

    def fake_run_to_zarr(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli_mod, "run_to_zarr", fake_run_to_zarr)
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        cli_mod.to_zarr,
        [
            "--stac-catalog",
            str(catalog_dir),
            "--titiler-eopf-compatible",
        ],
    )

    assert result.exit_code == 0
    assert captured["titiler_eopf_compatible"] is True


def test_cli_forwards_stac_object_type(tmp_path, monkeypatch):
    captured = {}

    def fake_run_to_zarr(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli_mod, "run_to_zarr", fake_run_to_zarr)
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        cli_mod.to_zarr,
        [
            "--stac-catalog",
            str(catalog_dir),
            "--stac-object-type",
            "item",
        ],
    )

    assert result.exit_code == 0
    assert captured["stac_object_type"] == "item"


def test_ensure_unique_time_index_deduplicates():
    ds = Dataset(
        data_vars={
            "v": (
                ("time", "y", "x"),
                np.arange(4 * 2 * 2, dtype=np.float32).reshape(4, 2, 2),
            )
        },
        coords={
            "time": np.array([10, 10, 20, 30], dtype=np.int64),
            "y": np.array([0.0, 1.0], dtype=np.float64),
            "x": np.array([0.0, 1.0], dtype=np.float64),
        },
    )

    out = ensure_unique_time_index(ds)
    assert out.sizes["time"] == 3
    assert out["time"].values.tolist() == [10, 20, 30]


def test_ensure_unique_time_index_noop_when_unique():
    ds = Dataset(
        data_vars={
            "v": (
                ("time", "y", "x"),
                np.arange(3 * 2 * 2, dtype=np.float32).reshape(3, 2, 2),
            )
        },
        coords={
            "time": np.array([10, 20, 30], dtype=np.int64),
            "y": np.array([0.0, 1.0], dtype=np.float64),
            "x": np.array([0.0, 1.0], dtype=np.float64),
        },
    )

    out = ensure_unique_time_index(ds)
    assert out.sizes["time"] == 3
    assert out["time"].values.tolist() == [10, 20, 30]


def test_format_time_values_for_summaries_datetime_unique_sorted():
    ds = Dataset(
        data_vars={
            "v": (
                ("time", "y", "x"),
                np.arange(3 * 1 * 1, dtype=np.float32).reshape(3, 1, 1),
            )
        },
        coords={
            "time": np.array(
                [
                    "2021-06-28T10:23:24.330000000",
                    "2021-06-28T10:23:24.330000000",
                    "2021-06-28T10:23:24.331000000",
                ],
                dtype="datetime64[ns]",
            ),
            "y": np.array([0.0], dtype=np.float64),
            "x": np.array([0.0], dtype=np.float64),
        },
    )

    values = format_time_values_for_summaries(ds)
    assert values == [
        "2021-06-28T10:23:24.330000000Z",
        "2021-06-28T10:23:24.331000000Z",
    ]


def test_normalize_renders_for_zarr_propagates_and_rewrites_assets():
    input_renders = {
        "ndwi_default": {
            "assets": ["ndwi"],
            "rescale": [[-1, 1]],
            "colormap_name": "viridis",
        }
    }

    out = normalize_renders_for_zarr(input_renders, ["ndwi", "water-bodies"])
    assert out is not None
    assert out["ndwi_default"]["assets"] == ["measurements"]
    assert out["ndwi_default"]["expression"] == "/measurements:ndwi"
    assert out["ndwi_default"]["colormap_name"] == "viridis"


def test_normalize_renders_for_zarr_keeps_expression_if_present():
    input_renders = {
        "custom": {
            "assets": ["water-bodies"],
            "expression": "/measurements:water-bodies",
        }
    }
    out = normalize_renders_for_zarr(input_renders, ["ndwi", "water-bodies"])
    assert out is not None
    assert out["custom"]["assets"] == ["measurements"]
    assert out["custom"]["expression"] == "/measurements:water-bodies"


def test_to_pystac_renders_returns_render_objects():
    normalized = {
        "ndwi_default": {
            "assets": ["measurements"],
            "expression": "/measurements:ndwi",
            "rescale": [[-1, 1]],
        }
    }
    renders = to_pystac_renders(normalized)
    assert renders is not None
    assert "ndwi_default" in renders
    assert renders["ndwi_default"].to_dict()["expression"] == "/measurements:ndwi"
