#!/usr/bin/env python3
"""Validate the repository TileMatrixSet-based multiscales profile."""

from __future__ import annotations

from stac_zarr.multiscales import build_tile_matrix_limits, build_tile_matrix_set
from stac_zarr.reducers import to_resampling_method


def build_multiscales_payload() -> dict:
    tile_matrix_set = build_tile_matrix_set(
        proj_code="EPSG:32633",
        affine_6=[10.0, 0.0, 300000.0, 0.0, -10.0, 5000000.0],
        base_shape=[[1094, 1094], [547, 547], [273, 273]],
        chunk_shape=[512, 512],
    )
    tile_matrix_limits = build_tile_matrix_limits(tile_matrix_set)
    return {
        "resampling_method": to_resampling_method("mean"),
        "tile_matrix_set": tile_matrix_set,
        "tile_matrix_limits": tile_matrix_limits,
    }


def main() -> int:
    payload = build_multiscales_payload()
    tms = payload.get("tile_matrix_set", {})
    matrices_list = tms.get("tileMatrices", [])
    matrices = {m["id"]: m for m in matrices_list if isinstance(m, dict) and "id" in m}
    limits = payload.get("tile_matrix_limits") or []

    if len(limits) != len(matrices):
        print("multiscales TMS-profile validation: FAIL")
        print("tile_matrix_limits length does not match tileMatrices length")
        return 1

    for limit in limits:
        tile_matrix_id = limit.get("tileMatrix")
        matrix = matrices.get(tile_matrix_id)
        if matrix is None:
            print("multiscales TMS-profile validation: FAIL")
            print(f"limit references unknown tileMatrix '{tile_matrix_id}'")
            return 1
        min_row = int(limit.get("minTileRow", -1))
        min_col = int(limit.get("minTileCol", -1))
        max_row = int(limit.get("maxTileRow", -1))
        max_col = int(limit.get("maxTileCol", -1))
        if min_row < 0 or min_col < 0:
            print("multiscales TMS-profile validation: FAIL")
            print(f"negative minimum tile index for '{tile_matrix_id}'")
            return 1
        if min_row > max_row or min_col > max_col:
            print("multiscales TMS-profile validation: FAIL")
            print(f"invalid min/max ordering for '{tile_matrix_id}'")
            return 1
        matrix_height = int(matrix.get("matrixHeight", 0))
        matrix_width = int(matrix.get("matrixWidth", 0))
        if max_row >= matrix_height or max_col >= matrix_width:
            print("multiscales TMS-profile validation: FAIL")
            print(f"tile limits exceed matrix dimensions for '{tile_matrix_id}'")
            return 1

    print("multiscales TMS-profile validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
