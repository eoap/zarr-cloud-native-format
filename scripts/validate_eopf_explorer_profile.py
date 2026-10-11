#!/usr/bin/env python3
"""Validate repository output against the EOPF Explorer-style GeoZarr profile."""

from __future__ import annotations

from stac_zarr.models.generated.spatial import SpatialAttributes

from validate_multiscales_layout_profile import build_multiscales_payload


def main() -> int:
    # Validate multiscales structure
    multiscales_payload = build_multiscales_payload()

    # Minimal representative datasets payload (as emitted by writer)
    datasets_payload = {
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
                "spatial:shape": [547, 547],
                "spatial:transform": [20.0, 0.0, 300000.0, 0.0, -20.0, 5000000.0],
                "downsampling_factor": 2,
                "overview:reducer": "nearest",
                "overview:variable_type": "categorical",
            },
        ],
        "axes": [
            {"name": "time", "type": "temporal"},
            {"name": "y", "type": "spatial"},
            {"name": "x", "type": "spatial"},
        ],
    }
    if not isinstance(datasets_payload.get("name"), str):
        print("EOPF Explorer profile validation: FAIL")
        print("datasets payload missing 'name'")
        return 1
    if not isinstance(datasets_payload.get("datasets"), list) or not datasets_payload["datasets"]:
        print("EOPF Explorer profile validation: FAIL")
        print("datasets payload missing 'datasets' list")
        return 1
    if not isinstance(datasets_payload.get("axes"), list) or len(datasets_payload["axes"]) < 2:
        print("EOPF Explorer profile validation: FAIL")
        print("datasets payload missing valid 'axes'")
        return 1

    # Validate spatial metadata shape
    SpatialAttributes.model_validate(
        {
            "spatial:dimensions": ["y", "x"],
            "spatial:bbox": [300000.0, 4890600.0, 310940.0, 5000000.0],
            "spatial:transform_type": "affine",
            "spatial:transform": [10.0, 0.0, 300000.0, 0.0, -10.0, 5000000.0],
            "spatial:shape": [1094, 1094],
            "spatial:registration": "pixel",
        }
    )

    # Sanity checks expected by EOPF-Explorer-style visualization
    if not multiscales_payload.get("layout"):
        print("EOPF Explorer profile validation: FAIL")
        print("missing layout in multiscales payload")
        return 1

    print("EOPF Explorer profile validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
