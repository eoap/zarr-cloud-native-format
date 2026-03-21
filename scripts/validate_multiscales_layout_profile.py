#!/usr/bin/env python3
"""Validate the repository GeoZarr v1 multiscales layout profile."""

from __future__ import annotations

from stac_zarr.multiscales import build_v1_layout
from stac_zarr.reducers import to_resampling_method


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
        "resampling_method": to_resampling_method("mean"),
        "layout": build_v1_layout(entries),
    }


def main() -> int:
    payload = build_multiscales_payload()
    layout = payload.get("layout") or []
    if not layout:
        print("multiscales layout-profile validation: FAIL")
        print("layout is missing or empty")
        return 1

    assets = {entry.get("asset") for entry in layout if isinstance(entry, dict)}
    for idx, entry in enumerate(layout):
        if not isinstance(entry, dict):
            print("multiscales layout-profile validation: FAIL")
            print(f"layout entry {idx} is not an object")
            return 1
        asset = entry.get("asset")
        if not isinstance(asset, str) or not asset:
            print("multiscales layout-profile validation: FAIL")
            print(f"layout entry {idx} has invalid asset")
            return 1
        shape = entry.get("spatial:shape")
        transform = entry.get("spatial:transform")
        if not isinstance(shape, list) or len(shape) != 2:
            print("multiscales layout-profile validation: FAIL")
            print(f"layout entry {idx} has invalid spatial:shape")
            return 1
        if not isinstance(transform, list) or len(transform) != 6:
            print("multiscales layout-profile validation: FAIL")
            print(f"layout entry {idx} has invalid spatial:transform")
            return 1
        parent = entry.get("derived_from")
        if parent is not None and parent not in assets:
            print("multiscales layout-profile validation: FAIL")
            print(f"layout entry {idx} derived_from references unknown asset '{parent}'")
            return 1

    print("multiscales layout-profile validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
