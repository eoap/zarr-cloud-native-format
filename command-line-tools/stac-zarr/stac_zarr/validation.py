"""Validate emitted GeoZarr metadata and references on every store node."""

from collections.abc import Mapping
from pathlib import Path

import zarr
from geozarr_toolkit import validate_attrs
from zarr.core.metadata.v2 import ArrayV2Metadata
from zarr.core.metadata.v3 import ArrayV3Metadata

from stac_zarr.constants import GEO_PROJ_CONVENTION, MULTISCALES_CONVENTION, SPATIAL_CONVENTION

StoreArray = zarr.Array[ArrayV2Metadata] | zarr.Array[ArrayV3Metadata]

EXPECTED = {
    entry["uuid"]: entry
    for entry in (GEO_PROJ_CONVENTION, SPATIAL_CONVENTION, MULTISCALES_CONVENTION)
}


def _declaration_errors(attrs: Mapping[str, object], location: str) -> tuple[set[str], list[str]]:
    declared: set[str] = set()
    errors: list[str] = []
    entries = attrs.get("zarr_conventions", [])
    if not isinstance(entries, list):
        return declared, [f"{location}: invalid convention declaration"]
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append(f"{location}: invalid convention declaration")
            continue
        uuid = entry.get("uuid")
        if isinstance(uuid, str) and uuid in EXPECTED:
            declared.add(uuid)
            for field, value in EXPECTED[uuid].items():
                if entry.get(field) != value:
                    errors.append(
                        f"{location}: {EXPECTED[uuid]['name']} declaration: incorrect {field}"
                    )
    return declared, errors


def _required_conventions(
    node: zarr.Group | StoreArray, attrs: Mapping[str, object], is_root: bool, location: str
) -> tuple[list[dict[str, str]], list[str]]:
    required = list(EXPECTED.values()) if is_root else []
    errors: list[str] = []
    for prefix, convention in (("proj:", GEO_PROJ_CONVENTION), ("spatial:", SPATIAL_CONVENTION)):
        if any(key.startswith(prefix) for key in attrs):
            required.append(convention)
    if "multiscales" in attrs:
        required.append(MULTISCALES_CONVENTION)
    if isinstance(node, zarr.Array) and "grid_mapping" in attrs:
        required.extend([GEO_PROJ_CONVENTION, SPATIAL_CONVENTION])
        if not any(key.startswith("proj:") for key in attrs):
            errors.append(f"{location}: missing array projection metadata")
        if "spatial:dimensions" not in attrs:
            errors.append(f"{location}: missing array spatial metadata")
    return required, errors


def _spatial_array_errors(
    node: StoreArray, attrs: Mapping[str, object], location: str
) -> list[str]:
    if "spatial:dimensions" not in attrs:
        return []
    metadata = node.metadata
    names = (metadata.dimension_names or ()) if isinstance(metadata, ArrayV3Metadata) else ()
    dims = attrs["spatial:dimensions"]
    if not isinstance(dims, list) or not all(dim in names for dim in dims):
        return [f"{location}: spatial dimensions absent from dimension_names"]
    if attrs.get("spatial:shape") != [node.shape[names.index(dim)] for dim in dims]:
        return [f"{location}: spatial:shape disagrees with array shape"]
    return []


def _layout_array_errors(
    child: zarr.Group | StoreArray, entry: Mapping[str, object], target: str, location: str
) -> list[str]:
    arrays = (
        [child]
        if isinstance(child, zarr.Array)
        else [array for _, array in child.arrays() if "spatial:shape" in array.attrs]
    )
    if not arrays:
        return [f"{location}: {target}: layout asset contains no spatial arrays"]
    errors: list[str] = []
    for array in arrays:
        for key in ("spatial:shape", "spatial:transform"):
            if key in entry and entry[key] != array.attrs.get(key):
                errors.append(f"{location}: {target}: layout {key} disagrees with array")
    return errors


def _layout_entry_errors(
    node: zarr.Group, entry: Mapping[str, object], assets: set[str], location: str
) -> list[str]:
    errors: list[str] = []
    for field in ("asset", "derived_from"):
        target = entry.get(field)
        if target is None:
            continue
        if not isinstance(target, str):
            errors.append(f"{location}: multiscales {field} missing: {target}")
            continue
        try:
            child = node[target]
        except (KeyError, TypeError, ValueError):
            errors.append(f"{location}: multiscales {field} missing: {target}")
            continue
        if field == "derived_from" and target not in assets:
            errors.append(f"{location}: derived_from absent from layout: {target}")
        if field == "asset":
            errors.extend(_layout_array_errors(child, entry, target, location))
    return errors


def _layout_errors(node: zarr.Group, attrs: Mapping[str, object], location: str) -> list[str]:
    multiscales = attrs.get("multiscales", {})
    layout = multiscales.get("layout", []) if isinstance(multiscales, dict) else []
    if not isinstance(layout, list):
        return []
    entries = [entry for entry in layout if isinstance(entry, dict)]
    assets = {entry["asset"] for entry in entries if isinstance(entry.get("asset"), str)}
    errors: list[str] = []
    for entry in entries:
        errors.extend(_layout_entry_errors(node, entry, assets, location))
    return errors


def _check_node(node: zarr.Group | StoreArray, path: str, root: zarr.Group) -> list[str]:
    attrs: dict[str, object] = dict(node.attrs)
    location = path or "/"
    errors = [
        f"{location}: {convention}: {failure}"
        for convention, failures in validate_attrs(attrs).items()
        for failure in failures
    ]
    if errors:
        # The official Toolkit rejects malformed structures before deeper inspection.
        return errors
    declared, errors = _declaration_errors(attrs, location)
    required, missing_metadata = _required_conventions(node, attrs, node is root, location)
    errors.extend(missing_metadata)
    errors.extend(
        f"{location}: missing {convention['name']} declaration"
        for convention in required
        if convention["uuid"] not in declared
    )
    if isinstance(node, zarr.Array):
        errors.extend(_spatial_array_errors(node, attrs, location))
    else:
        errors.extend(_layout_errors(node, attrs, location))
        for name, child in node.members():
            errors.extend(_check_node(child, f"{path}/{name}" if path else name, root))
    return errors


def validate_geozarr_store(store: zarr.Group | str | Path) -> None:
    """Validate official convention schemas and actual array/pyramid references.

    The Toolkit owns attribute schema validation. Additional checks ensure
    declarations match the published convention versions, spatial axes and
    shapes match real arrays, and multiscale references identify store nodes.
    """
    root = (
        store
        if isinstance(store, zarr.Group)
        else zarr.open_group(str(store), mode="r", use_consolidated=False)
    )
    errors = _check_node(root, "", root)
    if errors:
        raise ValueError("GeoZarr validation failed:\n" + "\n".join(errors))
