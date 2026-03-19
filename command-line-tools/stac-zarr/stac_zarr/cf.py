from typing import Any, Dict, List, Tuple

import numpy as np
from xarray import DataArray


def _coerce_time_values(values: np.ndarray) -> Tuple[np.ndarray, Dict[str, str]]:
    """Convert time coordinates to CF-style numeric values when possible."""
    if np.issubdtype(values.dtype, np.datetime64):
        epoch_seconds = values.astype("datetime64[s]").astype(np.int64)
        return epoch_seconds, {
            "standard_name": "time",
            "units": "seconds since 1970-01-01T00:00:00Z",
            "calendar": "proleptic_gregorian",
        }
    try:
        return np.asarray(values, dtype=np.int64), {
            "standard_name": "time",
            "units": "1",
        }
    except (TypeError, ValueError):
        return np.arange(values.shape[0], dtype=np.int64), {
            "standard_name": "time",
            "units": "1",
        }


def write_cf_dataset_members(
    dataset_group: Any,
    da: DataArray,
    transform_6: List[float],
    crs_wkt: str,
) -> None:
    """Write coordinate arrays and spatial_ref required by CF-style dataset layout."""
    if "time" in da.dims:
        raw_time_vals = da.coords["time"].values if "time" in da.coords else np.arange(da.sizes["time"])
        time_vals, time_attrs = _coerce_time_values(np.asarray(raw_time_vals))
        time_arr = dataset_group.create(
            name="time",
            shape=(time_vals.shape[0],),
            chunks=(max(1, min(1024, time_vals.shape[0])),),
            dtype=time_vals.dtype,
            overwrite=True,
            dimension_names=["time"],
            attributes=time_attrs,
        )
        time_arr[...] = time_vals

    if "y" in da.dims:
        y_vals = np.asarray(da.coords["y"].values, dtype=np.float64)
        y_arr = dataset_group.create(
            name="y",
            shape=(y_vals.shape[0],),
            chunks=(max(1, min(4096, y_vals.shape[0])),),
            dtype=y_vals.dtype,
            overwrite=True,
            dimension_names=["y"],
            attributes={"standard_name": "projection_y_coordinate", "units": "m"},
        )
        y_arr[...] = y_vals

    if "x" in da.dims:
        x_vals = np.asarray(da.coords["x"].values, dtype=np.float64)
        x_arr = dataset_group.create(
            name="x",
            shape=(x_vals.shape[0],),
            chunks=(max(1, min(4096, x_vals.shape[0])),),
            dtype=x_vals.dtype,
            overwrite=True,
            dimension_names=["x"],
            attributes={"standard_name": "projection_x_coordinate", "units": "m"},
        )
        x_arr[...] = x_vals

    spatial_ref_arr = dataset_group.create(
        name="spatial_ref",
        shape=(),
        chunks=(),
        dtype=np.int32,
        overwrite=True,
        dimension_names=[],
        attributes={
            "crs_wkt": crs_wkt,
            "spatial_ref": crs_wkt,
            "GeoTransform": (
                f"{transform_6[2]} {transform_6[0]} {transform_6[1]} "
                f"{transform_6[5]} {transform_6[3]} {transform_6[4]}"
            ),
        },
    )
    spatial_ref_arr[...] = np.int32(0)


def _iter_data_array_names(dataset_group: Any) -> List[str]:
    """Return non-coordinate data array names from a dataset group."""
    names = list(dataset_group.array_keys())
    return [name for name in names if name not in {"time", "y", "x", "spatial_ref"}]


def check_grid_mapping(dataset_group: Any) -> None:
    """Ensure grid_mapping declared by each data array points to an existing member."""
    members = set(dataset_group.array_keys()) | set(dataset_group.group_keys())
    for name in _iter_data_array_names(dataset_group):
        arr = dataset_group[name]
        grid_mapping = arr.attrs.get("grid_mapping")
        if isinstance(grid_mapping, str) and grid_mapping not in members:
            raise ValueError(
                f"Grid mapping variable '{grid_mapping}' declared by {name} was not found in dataset members"
            )


def check_valid_coordinates(dataset_group: Any) -> None:
    """Ensure coordinate variables referenced by dimensions and attrs exist and match shape."""
    members = set(dataset_group.array_keys()) | set(dataset_group.group_keys())
    for name in _iter_data_array_names(dataset_group):
        arr = dataset_group[name]
        dims = tuple(getattr(arr, "dimension_names", ()) or ())
        if not dims:
            dims = tuple(getattr(getattr(arr, "metadata", None), "dimension_names", ()) or ())
        if not dims:
            continue

        for idx, dim in enumerate(dims):
            if dim not in members:
                raise ValueError(
                    f"Dimension '{dim}' for array '{name}' is not defined in the model members."
                )
            dim_member = dataset_group[dim]
            if len(dim_member.shape) != 1:
                raise ValueError(
                    f"Dimension '{dim}' for array '{name}' should be a 1D coordinate variable."
                )
            if dim_member.shape[0] != arr.shape[idx]:
                raise ValueError(
                    f"Dimension '{dim}' for array '{name}' has a shape mismatch: "
                    f"{dim_member.shape[0]} != {arr.shape[idx]}."
                )

        coordinates_attr = arr.attrs.get("coordinates")
        if isinstance(coordinates_attr, str):
            for coord_name in coordinates_attr.split():
                if coord_name not in members:
                    raise ValueError(
                        f"Coordinate '{coord_name}' for array '{name}' is not defined in the model members."
                    )


def validate_dataset_group(dataset_group: Any) -> None:
    """Run GeoZarr-style coordinate and grid-mapping checks for a dataset group."""
    check_valid_coordinates(dataset_group)
    check_grid_mapping(dataset_group)
