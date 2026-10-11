"""Validate emitted GeoZarr metadata and references on every store node."""

from pathlib import Path
from typing import Any

import zarr
from geozarr_toolkit import validate_attrs

from stac_zarr.constants import (
    GEO_PROJ_CONVENTION,
    MULTISCALES_CONVENTION,
    SPATIAL_CONVENTION,
)


def validate_geozarr_store(store: zarr.Group | str | Path) -> None:
    """Raise ValueError for invalid metadata, declarations, or pyramid references.

    Toolkit attribute validation is complemented by checks on the actual store:
    declarations must identify our published version, and spatial axes, shapes,
    and multiscale paths must agree with the arrays they describe. CF coordinate
    arrays do not need to declare these conventions.
    """
    root = (
        store
        if isinstance(store, zarr.Group)
        else zarr.open_group(str(store), mode="r", use_consolidated=False)
    )
    errors: list[str] = []
    expected = {
        entry["uuid"]: entry
        for entry in (GEO_PROJ_CONVENTION, SPATIAL_CONVENTION, MULTISCALES_CONVENTION)
    }

    def check(node: Any, path: str) -> None:
        attrs = dict(node.attrs)
        location = path or "/"
        invalid_attrs = False
        for convention, failures in validate_attrs(attrs).items():
            errors.extend(
                f"{location}: {convention}: {failure}" for failure in failures
            )
            invalid_attrs |= bool(failures)
        if invalid_attrs:
            # Do not inspect malformed structures after the Toolkit rejects them.
            return

        declared: set[str] = set()
        for entry in attrs.get("zarr_conventions", []):
            if not isinstance(entry, dict):
                errors.append(f"{location}: invalid convention declaration")
                continue
            uuid = entry.get("uuid")
            if uuid in expected:
                declared.add(uuid)
                for field, value in expected[uuid].items():
                    if entry.get(field) != value:
                        errors.append(
                            f"{location}: {expected[uuid]['name']} declaration: incorrect {field}"
                        )

        required = list(expected.values()) if node is root else []
        if any(key.startswith("proj:") for key in attrs):
            required.append(GEO_PROJ_CONVENTION)
        if any(key.startswith("spatial:") for key in attrs):
            required.append(SPATIAL_CONVENTION)
        if "multiscales" in attrs:
            required.append(MULTISCALES_CONVENTION)
        if isinstance(node, zarr.Array) and "grid_mapping" in attrs:
            required.extend([GEO_PROJ_CONVENTION, SPATIAL_CONVENTION])
            if not any(key.startswith("proj:") for key in attrs):
                errors.append(f"{location}: missing array projection metadata")
            if "spatial:dimensions" not in attrs:
                errors.append(f"{location}: missing array spatial metadata")
        for convention in required:
            if convention["uuid"] not in declared:
                errors.append(f"{location}: missing {convention['name']} declaration")

        if isinstance(node, zarr.Array) and "spatial:dimensions" in attrs:
            names = node.metadata.dimension_names or ()
            dims = attrs["spatial:dimensions"]
            if not all(dim in names for dim in dims):
                errors.append(
                    f"{location}: spatial dimensions absent from dimension_names"
                )
            elif attrs.get("spatial:shape") != [
                node.shape[names.index(dim)] for dim in dims
            ]:
                errors.append(f"{location}: spatial:shape disagrees with array shape")

        if isinstance(node, zarr.Group):
            multiscales = attrs.get("multiscales", {})
            layout = (
                multiscales.get("layout", []) if isinstance(multiscales, dict) else []
            )
            assets = {entry.get("asset") for entry in layout if isinstance(entry, dict)}
            for entry in layout:
                if not isinstance(entry, dict):
                    continue
                for field in ("asset", "derived_from"):
                    target = entry.get(field)
                    if target is None:
                        continue
                    try:
                        child = node[target]
                    except (KeyError, TypeError, ValueError):
                        errors.append(
                            f"{location}: multiscales {field} missing: {target}"
                        )
                        continue
                    if field == "derived_from" and target not in assets:
                        errors.append(
                            f"{location}: derived_from absent from layout: {target}"
                        )
                    if field == "asset":
                        arrays = (
                            [child]
                            if isinstance(child, zarr.Array)
                            else [
                                array
                                for _, array in child.arrays()
                                if "spatial:shape" in array.attrs
                            ]
                        )
                        if not arrays:
                            errors.append(
                                f"{location}: {target}: layout asset contains no spatial arrays"
                            )
                        for array in arrays:
                            for key in ("spatial:shape", "spatial:transform"):
                                if key in entry and entry[key] != array.attrs.get(key):
                                    errors.append(
                                        f"{location}: {target}: layout {key} disagrees with array"
                                    )
            for name, child in node.members():
                check(child, f"{path}/{name}" if path else name)

    check(root, "")
    if errors:
        raise ValueError("GeoZarr validation failed:\n" + "\n".join(errors))
