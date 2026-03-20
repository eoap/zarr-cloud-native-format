#!/usr/bin/env python3
"""Validate the repository TileMatrixSet-based multiscales profile."""

from __future__ import annotations

from stac_zarr.models.multiscales import Multiscales
from stac_zarr.models.multiscales import TileMatrixLimit, TileMatrixSet
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
    multiscales = Multiscales(
        resampling_method=to_resampling_method("mean"),
        tile_matrix_set=TileMatrixSet.model_validate(tile_matrix_set),
        tile_matrix_limits=[
            TileMatrixLimit.model_validate(limit)
            for limit in tile_matrix_limits
        ],
    )
    return multiscales.model_dump(by_alias=True, exclude_none=True)


def main() -> int:
    payload = build_multiscales_payload()
    model = Multiscales.model_validate(payload)

    matrices = {m.id: m for m in model.tile_matrix_set.tile_matrices}
    limits = model.tile_matrix_limits or []

    if len(limits) != len(matrices):
        print("multiscales TMS-profile validation: FAIL")
        print("tile_matrix_limits length does not match tileMatrices length")
        return 1

    for limit in limits:
        matrix = matrices.get(limit.tile_matrix)
        if matrix is None:
            print("multiscales TMS-profile validation: FAIL")
            print(f"limit references unknown tileMatrix '{limit.tile_matrix}'")
            return 1
        if limit.min_tile_row < 0 or limit.min_tile_col < 0:
            print("multiscales TMS-profile validation: FAIL")
            print(f"negative minimum tile index for '{limit.tile_matrix}'")
            return 1
        if limit.min_tile_row > limit.max_tile_row or limit.min_tile_col > limit.max_tile_col:
            print("multiscales TMS-profile validation: FAIL")
            print(f"invalid min/max ordering for '{limit.tile_matrix}'")
            return 1
        if limit.max_tile_row >= matrix.matrix_height or limit.max_tile_col >= matrix.matrix_width:
            print("multiscales TMS-profile validation: FAIL")
            print(f"tile limits exceed matrix dimensions for '{limit.tile_matrix}'")
            return 1

    print("multiscales TMS-profile validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
