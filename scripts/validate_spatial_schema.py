#!/usr/bin/env python3
"""Validate emitted spatial metadata against the official schema."""

from __future__ import annotations

from eoap_http import read_json_object
from jsonschema import ValidationError, validate
from stac_zarr.constants import SPATIAL_CONVENTION
from stac_zarr.models.generated.spatial import ConventionMetadata as SpatialConventionMetadata

SPATIAL_SCHEMA_URL = SPATIAL_CONVENTION["schema_url"]


def fetch_schema(url: str) -> dict[str, object]:
    return read_json_object(url)


def build_spatial_payload() -> dict[str, object]:
    return {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": {
            "zarr_conventions": [
                SpatialConventionMetadata.model_validate(SPATIAL_CONVENTION).model_dump()
            ],
            "spatial:dimensions": ["y", "x"],
            "spatial:bbox": [300000.0, 4989060.0, 310940.0, 5000000.0],
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
