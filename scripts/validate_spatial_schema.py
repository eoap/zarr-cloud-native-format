#!/usr/bin/env python3
"""Validate emitted spatial metadata against the official schema."""

from __future__ import annotations

import json
import urllib.request

from jsonschema import ValidationError, validate

from stac_zarr.models.conventions import SpatialConventionMetadata

SPATIAL_SCHEMA_URL = "https://raw.githubusercontent.com/zarr-conventions/spatial/main/schema.json"


def fetch_schema(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def build_spatial_payload() -> dict:
    return {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": {
            "zarr_conventions": [SpatialConventionMetadata().model_dump()],
            "spatial:dimensions": ["y", "x"],
            "spatial:bbox": [300000.0, 4890600.0, 310940.0, 5000000.0],
            "spatial:shape": [1094, 1094],
            "spatial:transform_type": "affine",
            "spatial:transform": [10.0, 0.0, 300000.0, 0.0, -10.0, 5000000.0],
            "spatial:registration": "pixel",
        },
    }


def main() -> int:
    schema = fetch_schema(SPATIAL_SCHEMA_URL)
    payload = build_spatial_payload()
    try:
        validate(instance=payload, schema=schema)
    except ValidationError as exc:
        print("spatial schema validation: FAIL")
        print(exc)
        return 1

    print("spatial schema validation: PASS")
    print(f"schema: {SPATIAL_SCHEMA_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
