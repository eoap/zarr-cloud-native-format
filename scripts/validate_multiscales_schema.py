#!/usr/bin/env python3
"""Validate emitted multiscales metadata against the official schema."""

from __future__ import annotations

import json
import urllib.request

from jsonschema import ValidationError, validate

from stac_zarr.constants import MULTISCALES_CONVENTION
from stac_zarr.models.generated.multiscales import ConventionMetadata as MultiscalesConventionMetadata
from stac_zarr.multiscales import build_v1_layout
from stac_zarr.reducers import to_resampling_method


def fetch_schema(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def build_multiscales_payload() -> dict:
    entries = [
        {
            "name": "water-bodies",
            "datasets": [
                {
                    "path": "measurements/water-bodies",
                    "level": 0,
                    "spatial:shape": [1094, 1094],
                    "spatial:transform": [10.0, 0.0, 300000.0, 0.0, -10.0, 5000000.0],
                },
                {
                    "path": "measurements_overviews/water-bodies/1/water-bodies",
                    "level": 1,
                    "downsampling_factor": 2,
                    "overview:reducer": "nearest",
                    "spatial:shape": [547, 547],
                    "spatial:transform": [20.0, 0.0, 300000.0, 0.0, -20.0, 5000000.0],
                },
            ],
        }
    ]
    return {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": {
            "zarr_conventions": [
                MultiscalesConventionMetadata.model_validate(
                    {
                        "schema_url": "https://raw.githubusercontent.com/zarr-conventions/multiscales/refs/tags/v1/schema.json",
                        "spec_url": "https://github.com/zarr-conventions/multiscales/blob/v1/README.md",
                        "uuid": "d35379db-88df-4056-af3a-620245f8e347",
                        "name": "multiscales",
                        "description": "Multiscale layout of zarr datasets",
                    }
                ).model_dump()
            ],
            "multiscales": {
                "resampling_method": to_resampling_method("mean"),
                "layout": build_v1_layout(entries),
            },
        },
    }


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
