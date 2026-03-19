from xarray import DataArray


def get_variable_type(da: DataArray) -> str:
    """Classify variable as continuous or categorical from dtype."""
    if da.dtype.kind in ("f", "c"):
        return "continuous"
    return "categorical"


def downsample_2x(da: DataArray, reducer: str) -> DataArray:
    """Downsample spatial dims by 2 with selected reducer."""
    if reducer == "nearest":
        return da.isel(y=slice(None, None, 2), x=slice(None, None, 2))
    if reducer == "mean":
        return da.coarsen(y=2, x=2, boundary="trim").mean()
    if reducer == "max":
        return da.coarsen(y=2, x=2, boundary="trim").max()
    if reducer == "median":
        return da.coarsen(y=2, x=2, boundary="trim").median()
    raise ValueError(f"Unsupported overview reducer: {reducer}")


def to_resampling_method(reducer: str) -> str:
    """Map reducer names to GeoZarr resampling method literals."""
    if reducer == "mean":
        return "average"
    if reducer == "median":
        return "med"
    if reducer == "max":
        return "max"
    if reducer == "nearest":
        return "nearest"
    return "nearest"
