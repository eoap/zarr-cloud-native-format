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
