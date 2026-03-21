from typing import Any, Dict, List


def build_tile_matrix_set(
    proj_code: str,
    affine_6: List[float],
    base_shape: List[List[int]],
    chunk_shape: List[int],
) -> Dict[str, Any]:
    """Build a minimal TileMatrixSet from generated overview shapes."""
    point_of_origin = [float(affine_6[2]), float(affine_6[5])]
    cell_size = abs(float(affine_6[0]))
    tile_matrices = []

    for level, shape in enumerate(base_shape):
        y_size, x_size = int(shape[0]), int(shape[1])
        factor = 2**level
        level_cell_size = cell_size * factor
        tile_width = min(int(chunk_shape[1]), x_size)
        tile_height = min(int(chunk_shape[0]), y_size)
        tile_matrices.append(
            {
                "id": str(level),
                "scaleDenominator": level_cell_size / 0.00028,
                "cellSize": level_cell_size,
                "pointOfOrigin": point_of_origin,
                "tileWidth": tile_width,
                "tileHeight": tile_height,
                "matrixWidth": (x_size + tile_width - 1) // tile_width,
                "matrixHeight": (y_size + tile_height - 1) // tile_height,
            }
        )

    return {
        "id": f"{proj_code.replace(':', '_')}_multiscale",
        "title": f"{proj_code} multiscale pyramid",
        "crs": proj_code,
        "orderedAxes": ["E", "N"],
        "tileMatrices": tile_matrices,
    }


def build_tile_matrix_limits(tile_matrix_set: Dict[str, Any]) -> List[Dict[str, int | str]]:
    """Build OGC-style tile matrix limits from a TileMatrixSet."""
    limits: List[Dict[str, int | str]] = []
    for matrix in tile_matrix_set["tileMatrices"]:
        limits.append(
            {
                "tileMatrix": matrix["id"],
                "minTileRow": 0,
                "maxTileRow": int(matrix["matrixHeight"]) - 1,
                "minTileCol": 0,
                "maxTileCol": int(matrix["matrixWidth"]) - 1,
            }
        )
    return limits


def build_v1_layout(multiscales_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build GeoZarr v1 multiscales.layout entries from per-measurement datasets."""
    layout: List[Dict[str, Any]] = []

    for entry in multiscales_entries:
        datasets = sorted(entry.get("datasets", []), key=lambda ds: int(ds.get("level", 0)))
        previous_asset: str | None = None
        previous_factor: int = 1

        for ds in datasets:
            asset = ds.get("path")
            if not isinstance(asset, str) or not asset:
                continue

            current_factor = int(ds.get("downsampling_factor", 1))
            relative_scale = max(1, current_factor // max(1, previous_factor))
            layout_entry: Dict[str, Any] = {
                "asset": asset,
                "spatial:shape": ds.get("spatial:shape"),
                "spatial:transform": ds.get("spatial:transform"),
            }

            if previous_asset is not None:
                layout_entry["derived_from"] = previous_asset
                layout_entry["transform"] = {
                    "scale": [float(relative_scale), float(relative_scale)],
                    "translation": [0.0, 0.0],
                }
            if "overview:reducer" in ds:
                layout_entry["resampling_method"] = ds["overview:reducer"]

            layout.append(layout_entry)
            previous_asset = asset
            previous_factor = current_factor

    return layout
