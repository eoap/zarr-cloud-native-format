#!/usr/bin/env python3
"""Validate emitted geo-proj metadata against the official schema."""

from __future__ import annotations

import json
import urllib.request

from jsonschema import ValidationError, validate

from stac_zarr.models.generated.geo_proj import ConventionMetadata as GeoProjConventionMetadata

GEO_PROJ_SCHEMA_URL = "https://raw.githubusercontent.com/zarr-experimental/geo-proj/main/schema.json"


def fetch_schema(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def build_geo_proj_payload() -> dict:
    return {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": {
            "zarr_conventions": [
                GeoProjConventionMetadata.model_validate(
                    {
                        "schema_url": "https://raw.githubusercontent.com/zarr-experimental/geo-proj/refs/tags/v1/schema.json",
                        "spec_url": "https://github.com/zarr-experimental/geo-proj/blob/v1/README.md",
                        "uuid": "f17cb550-5864-4468-aeb7-f3180cfb622f",
                        "name": "proj:",
                        "description": "Coordinate reference system information for geospatial data",
                    }
                ).model_dump()
            ],
            # Strict geo-proj oneOf: emit exactly one projection representation
            "proj:code": "EPSG:32633",
        },
    }


def main() -> int:
    schema = fetch_schema(GEO_PROJ_SCHEMA_URL)
    payload = build_geo_proj_payload()
    try:
        validate(instance=payload, schema=schema)
    except ValidationError as exc:
        print("geo-proj schema validation: FAIL")
        print(exc)
        return 1

    print("geo-proj schema validation: PASS")
    print(f"schema: {GEO_PROJ_SCHEMA_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
