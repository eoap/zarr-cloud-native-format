#!/usr/bin/env python3
"""Validate emitted multiscales metadata against the official schema."""

from __future__ import annotations

import json
import urllib.request

from jsonschema import ValidationError, validate

from stac_zarr.constants import MULTISCALES_CONVENTION
from stac_zarr.models.multiscales import Multiscales, TileMatrixLimit, TileMatrixSet
from stac_zarr.multiscales import build_tile_matrix_limits, build_tile_matrix_set
from stac_zarr.reducers import to_resampling_method


def fetch_schema(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


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
    schema_url = MULTISCALES_CONVENTION["schema_url"]
    schema = fetch_schema(schema_url)
    payload = build_multiscales_payload()

    try:
        validate(instance=payload, schema=schema)
    except ValidationError as exc:
        print("multiscales schema validation: FAIL")
        print(exc)
        return 1

    print("multiscales schema validation: PASS")
    print(f"schema: {schema_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
