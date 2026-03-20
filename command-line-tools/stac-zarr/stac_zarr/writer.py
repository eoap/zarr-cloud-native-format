import os
import json
import copy
from pathlib import Path
from typing import Any, Dict, List

import dask.array
import numpy as np
import zarr
from loguru import logger
from odc.stac import stac_load
from pystac import (
    Asset,
    Catalog,
    CatalogType,
    Collection,
    Extent,
    Item,
    Link,
    STACObject,
    SpatialExtent,
    TemporalExtent,
    read_file as read_stac_file,
)
from pystac.extensions.datacube import DatacubeExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterBand, RasterExtension
from pystac.extensions.render import Render, RenderExtension
from xarray import DataArray, Dataset
from zarr.types import AnyArray

from stac_zarr.cf import validate_dataset_group, write_cf_dataset_members
from stac_zarr.constants import (
    STAC_EXTENSION_URIS,
    ZARR_V3_MULTISCALES_MEDIA_TYPE,
)
from stac_zarr.models.generated.geo_proj import ConventionMetadata as GeoProjConventionMetadata
from stac_zarr.models.generated.multiscales import ConventionMetadata as MultiscalesConventionMetadata
from stac_zarr.models.generated.spatial import (
    ConventionMetadata as SpatialConventionMetadata,
    SpatialAttributes,
)
from stac_zarr.contract import (
    extract_crs,
    get_measurement_keys,
    get_spatial_extent,
    get_temporal_extent,
    validate_items_have_measurements,
)
from stac_zarr.multiscales import build_tile_matrix_limits, build_tile_matrix_set
from stac_zarr.reducers import downsample_2x, get_variable_type, to_resampling_method


def build_root_proj_metadata(crs_obj: Any, proj_code: str) -> Dict[str, Any]:
    """Build root projection metadata with strict one-of semantics."""
    try:
        if hasattr(crs_obj, "to_json_dict"):
            projjson = crs_obj.to_json_dict()
        elif hasattr(crs_obj, "to_json"):
            json_text = crs_obj.to_json()
            projjson = json.loads(json_text) if isinstance(json_text, str) else json_text
        else:
            projjson = None

        if isinstance(projjson, dict):
            return {"proj:projjson": projjson}
    except Exception:
        pass

    try:
        return {"proj:wkt2": crs_obj.to_wkt("WKT2_2019")}
    except Exception:
        return {"proj:code": proj_code}


def _convention_metadata_models() -> list[dict[str, Any]]:
    """Build convention metadata entries validated by generated models."""
    return [
        MultiscalesConventionMetadata.model_validate(
            {
                "schema_url": "https://raw.githubusercontent.com/zarr-conventions/multiscales/refs/tags/v1/schema.json",
                "spec_url": "https://github.com/zarr-conventions/multiscales/blob/v1/README.md",
                "uuid": "d35379db-88df-4056-af3a-620245f8e347",
                "name": "multiscales",
                "description": "Multiscale layout of zarr datasets",
            }
        ).model_dump(),
        GeoProjConventionMetadata.model_validate(
            {
                "schema_url": "https://raw.githubusercontent.com/zarr-experimental/geo-proj/refs/tags/v1/schema.json",
                "spec_url": "https://github.com/zarr-experimental/geo-proj/blob/v1/README.md",
                "uuid": "f17cb550-5864-4468-aeb7-f3180cfb622f",
                "name": "proj:",
                "description": "Coordinate reference system information for geospatial data",
            }
        ).model_dump(),
        SpatialConventionMetadata.model_validate(
            {
                "schema_url": "https://raw.githubusercontent.com/zarr-conventions/spatial/refs/tags/v1/schema.json",
                "spec_url": "https://github.com/zarr-conventions/spatial/blob/v1/README.md",
                "uuid": "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4",
                "name": "spatial:",
                "description": "Spatial coordinate information",
            }
        ).model_dump(),
    ]


def consolidate_zarr_store(store_path: Path) -> None:
    """Write consolidated metadata for a Zarr store path."""
    zarr.consolidate_metadata(store_path)


def ensure_unique_time_index(dataset: Dataset) -> Dataset:
    """Ensure the dataset time coordinate is unique for robust label-based selection.

    TiTiler-EOPF uses xarray `.sel()` for time-based requests. Non-unique time indexes
    can raise reindexing errors. We keep the first occurrence for duplicate timestamps.
    """
    if "time" not in dataset.dims:
        return dataset

    time_values = np.asarray(dataset["time"].values)
    if time_values.size <= 1:
        return dataset

    _, first_indices = np.unique(time_values, return_index=True)
    if first_indices.size == time_values.size:
        return dataset

    keep_indices = np.sort(first_indices)
    dropped = int(time_values.size - keep_indices.size)
    logger.warning(
        f"Detected duplicate time coordinates ({dropped} duplicates). "
        "Keeping first occurrence per timestamp for stable time selection."
    )
    return dataset.isel(time=keep_indices)


def format_time_values_for_summaries(dataset: Dataset) -> List[str]:
    """Format dataset time coordinate as unique RFC3339 strings for STAC summaries."""
    if "time" not in dataset.coords:
        return []

    values = np.asarray(dataset["time"].values)
    if values.size == 0:
        return []

    if np.issubdtype(values.dtype, np.datetime64):
        unique_values = np.unique(values.astype("datetime64[ns]"))
        return [
            np.datetime_as_string(v, unit="ns", timezone="UTC")
            for v in unique_values
        ]

    unique_values = np.unique(values)
    return [str(v) for v in unique_values]


def _bbox_to_polygon(bbox: List[float]) -> Dict[str, Any]:
    """Convert [minx, miny, maxx, maxy] bbox to a GeoJSON polygon."""
    minx, miny, maxx, maxy = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [minx, miny],
                [minx, maxy],
                [maxx, maxy],
                [maxx, miny],
                [minx, miny],
            ]
        ],
    }


def normalize_renders_for_zarr(
    input_renders: Any, measurement_keys: List[str], output_asset_key: str = "measurements"
) -> Dict[str, Dict[str, Any]] | None:
    """Normalize Render extension payload for emitted Zarr STAC objects.

    Rules:
    * return None when input is missing/invalid
    * keep render ids and fields
    * normalize `assets` to point to output asset key
    * if `expression` is missing, derive from first matching input asset if possible
    """
    if not isinstance(input_renders, dict) or not input_renders:
        return None

    normalized: Dict[str, Dict[str, Any]] = {}
    for render_id, render_obj in input_renders.items():
        if not isinstance(render_obj, dict):
            continue

        out_obj: Dict[str, Any] = copy.deepcopy(render_obj)
        original_assets = render_obj.get("assets")
        matched_asset = None
        if isinstance(original_assets, list):
            matched_asset = next(
                (asset for asset in original_assets if isinstance(asset, str) and asset in measurement_keys),
                None,
            )
        elif isinstance(original_assets, str) and original_assets in measurement_keys:
            matched_asset = original_assets

        out_obj["assets"] = [output_asset_key]
        if "expression" not in out_obj and matched_asset is not None:
            out_obj["expression"] = f"/{output_asset_key}:{matched_asset}"

        normalized[str(render_id)] = out_obj

    return normalized or None


def to_pystac_renders(
    normalized_renders: Dict[str, Dict[str, Any]] | None,
) -> Dict[str, Render] | None:
    """Convert normalized render dicts into typed PySTAC Render objects."""
    if not normalized_renders:
        return None
    return {render_id: Render(copy.deepcopy(render_obj)) for render_id, render_obj in normalized_renders.items()}


def run_to_zarr(
    stac_catalog: Path,
    overview_levels: int,
    continuous_overview_reducer: str,
    categorical_overview_reducer: str,
    resolution: float | None = None,
    chunks: str = "manual",
    chunk_x: int = 512,
    chunk_y: int = 512,
    chunk_time: int = 1,
    consolidate: bool = True,
    titiler_eopf_compatible: bool = False,
    stac_object_type: str = "collection",
) -> None:
    logger.info(f"Reading STAC catalog from {stac_catalog}...")
    catalog: STACObject = read_stac_file(os.path.join(stac_catalog, "catalog.json"))

    if not isinstance(catalog, Catalog):
        raise Exception(
            f"{stac_catalog} is not a valid STAC Catalog instance, found {type(catalog)}"
        )

    collection = next(catalog.get_children())
    if not isinstance(collection, Collection):
        raise Exception(
            f"{stac_catalog} does not contain a valid STAC Collection instance, found {type(collection)}"
        )

    items: List[Item] = list(collection.get_all_items())
    if not items:
        raise ValueError("Input STAC Collection contains no items")

    logger.info(f"Found {len(items)} STAC Items in {stac_catalog} STAC Catalog")
    measurement_keys = get_measurement_keys(collection)
    validate_items_have_measurements(items, measurement_keys)

    crs = extract_crs(items[0])
    stac_load_kwargs: Dict[str, Any] = {
        "bands": measurement_keys,
        "crs": crs,
        "groupby": "time",
    }
    if chunks == "manual":
        stac_load_kwargs["chunks"] = {"x": chunk_x, "y": chunk_y, "time": chunk_time}
    if resolution is not None:
        stac_load_kwargs["resolution"] = resolution

    stac_catalog_dataset: Dataset = stac_load(items, **stac_load_kwargs)
    stac_catalog_dataset = ensure_unique_time_index(stac_catalog_dataset)

    logger.info("Loaded data using odc.stac")
    logger.info("Serializing the STAC Collection...")

    output_collection: Collection = Collection(
        id=collection.id,
        description=collection.description,
        title=collection.title,
        extent=Extent(
            spatial=SpatialExtent(bboxes=[get_spatial_extent(items)]),
            temporal=TemporalExtent([get_temporal_extent(items)]),
        ),
    )
    ProjectionExtension.summaries(output_collection, add_if_missing=True)
    RasterExtension.summaries(output_collection, add_if_missing=True)
    DatacubeExtension.ext(output_collection, add_if_missing=True)
    normalized_renders = normalize_renders_for_zarr(
        collection.extra_fields.get("renders"), measurement_keys, output_asset_key="measurements"
    )
    output_collection.stac_extensions = list(STAC_EXTENSION_URIS)
    time_summary_values = format_time_values_for_summaries(stac_catalog_dataset)
    if time_summary_values:
        output_collection.summaries.add("datetime", time_summary_values)
    pystac_renders = to_pystac_renders(normalized_renders)
    if pystac_renders is not None:
        RenderExtension.ext(output_collection, add_if_missing=True).renders = pystac_renders

    if stac_object_type not in {"collection", "item"}:
        raise ValueError("stac_object_type must be either 'collection' or 'item'")

    zarr_uri = f"{collection.id}.zarr"
    store_link = Link(
        rel="store",
        target=zarr_uri,
        media_type=ZARR_V3_MULTISCALES_MEDIA_TYPE,
        title=f"Zarr store for {collection.title}",
    )
    output_collection.add_link(store_link)

    spatial_bbox = [
        float(min(stac_catalog_dataset.x.values)),
        float(min(stac_catalog_dataset.y.values)),
        float(max(stac_catalog_dataset.x.values)),
        float(max(stac_catalog_dataset.y.values)),
    ]

    measurement_name = "measurements"
    gbox = stac_catalog_dataset.odc.geobox
    affine_6 = list(gbox.transform)[:6]
    proj_code = f"EPSG:{gbox.crs.epsg}" if gbox.crs.epsg is not None else crs.upper()

    root = zarr.open_group(Path(collection.id, zarr_uri), mode="w")
    measurements_grp = root.require_group(measurement_name)
    overviews_measurements_grp = (
        root.require_group(f"{measurement_name}_overviews")
        if overview_levels > 0
        else None
    )

    bands = []
    cube_variables = {}
    raster_bands = []
    multiscales_entries: List[Dict[str, Any]] = []
    multiscales_level_shapes: List[List[int]] = []
    default_resampling_method = to_resampling_method(categorical_overview_reducer)
    crs_wkt = gbox.crs.to_wkt("WKT2_2019")
    root_proj_metadata = build_root_proj_metadata(gbox.crs, proj_code)

    for measurement in measurement_keys:
        logger.info(f"Writing measurement {measurement} to Zarr store...")
        da: DataArray = stac_catalog_dataset[measurement].transpose("time", "y", "x")
        variable_type = get_variable_type(da)
        overview_reducer = (
            continuous_overview_reducer
            if variable_type == "continuous"
            else categorical_overview_reducer
        )
        if variable_type == "continuous":
            default_resampling_method = to_resampling_method(overview_reducer)

        title = collection.item_assets[measurement].title or measurement
        description = collection.item_assets[measurement].description or ""

        z: AnyArray = measurements_grp.create(
            name=measurement,
            shape=da.shape,
            chunks=da.data.chunksize,
            dtype=da.dtype,
            overwrite=True,
            attributes={
                "title": title,
                "description": description,
                "grid_mapping": "spatial_ref",
                "coordinates": "time y x",
            },
            dimension_names=["time", "y", "x"],
        )
        write_cf_dataset_members(measurements_grp, da, affine_6, crs_wkt)
        dask.array.store(da.data, z, lock=True)
        validate_dataset_group(measurements_grp)

        bands.append({"name": measurement, "description": description})
        cube_variables[measurement] = {"type": "data", "dimensions": ["time", "y", "x"]}
        raster_bands.append(
            RasterBand.create(
                data_type=da.dtype.name,
                nodata=None,
                spatial_resolution=[
                    abs(da.x.values[1] - da.x.values[0]),
                    abs(da.y.values[1] - da.y.values[0]),
                ],
            )
        )

        datasets = [
            {
                "path": f"{measurement_name}/{measurement}",
                "level": 0,
                "spatial:shape": [int(da.shape[1]), int(da.shape[2])],
                "spatial:transform": affine_6,
            }
        ]
        if not multiscales_level_shapes:
            multiscales_level_shapes.append([int(da.shape[1]), int(da.shape[2])])

        level_da = da
        for level in range(1, overview_levels + 1):
            if level_da.sizes["y"] < 2 or level_da.sizes["x"] < 2:
                logger.warning(
                    f"Stopping overview generation for {measurement} at level {level - 1}: "
                    f"spatial shape too small ({level_da.sizes['y']}, {level_da.sizes['x']})"
                )
                break

            level_da = downsample_2x(level_da, overview_reducer)
            if overviews_measurements_grp is None:
                break
            overviews_grp = overviews_measurements_grp.require_group(measurement)
            level_grp = overviews_grp.require_group(str(level))
            level_scale = 2**level
            level_affine_6 = [
                affine_6[0] * level_scale,
                affine_6[1],
                affine_6[2],
                affine_6[3],
                affine_6[4] * level_scale,
                affine_6[5],
            ]
            level_array: AnyArray = level_grp.create(
                name=measurement,
                shape=level_da.shape,
                chunks=level_da.data.chunksize,
                dtype=level_da.dtype,
                overwrite=True,
                attributes={
                    "title": title,
                    "description": f"{description} (overview level {level})",
                    "grid_mapping": "spatial_ref",
                    "coordinates": "time y x",
                },
                dimension_names=["time", "y", "x"],
            )
            write_cf_dataset_members(level_grp, level_da, level_affine_6, crs_wkt)
            dask.array.store(level_da.data, level_array, lock=True)
            validate_dataset_group(level_grp)

            datasets.append(
                {
                    "path": f"{measurement_name}_overviews/{measurement}/{level}/{measurement}",
                    "spatial:shape": [int(level_da.shape[1]), int(level_da.shape[2])],
                    "spatial:transform": level_affine_6,
                    "level": level,
                    "downsampling_factor": level_scale,
                    "overview:reducer": overview_reducer,
                    "overview:variable_type": variable_type,
                }
            )
            if len(multiscales_level_shapes) == level:
                multiscales_level_shapes.append([int(level_da.shape[1]), int(level_da.shape[2])])

        multiscales_entries.append(
            {
                "name": measurement,
                "datasets": datasets,
                "axes": [
                    {"name": "time", "type": "temporal"},
                    {"name": "y", "type": "spatial"},
                    {"name": "x", "type": "spatial"},
                ],
            }
        )

    tile_matrix_set = build_tile_matrix_set(
        proj_code=proj_code,
        affine_6=affine_6,
        base_shape=multiscales_level_shapes,
        chunk_shape=[int(stac_catalog_dataset.chunks["y"][0]), int(stac_catalog_dataset.chunks["x"][0])],
    )
    tile_matrix_limits = build_tile_matrix_limits(tile_matrix_set)

    multiscales_model = {
        "resampling_method": default_resampling_method,
        "tile_matrix_set": tile_matrix_set,
        "tile_matrix_limits": tile_matrix_limits,
    }
    spatial_model = SpatialAttributes.model_validate(
        {
            "spatial:dimensions": ["y", "x"],
            "spatial:bbox": spatial_bbox,
            "spatial:shape": list(gbox.shape),
            "spatial:transform_type": "affine",
            "spatial:transform": affine_6,
            "spatial:registration": "pixel",
        }
    )

    if not titiler_eopf_compatible:
        root.attrs.update(
            {
                "zarr_conventions": [
                    *_convention_metadata_models(),
                ],
                "multiscales": multiscales_model,
                "multiscales:datasets": multiscales_entries,
                **root_proj_metadata,
                **spatial_model.model_dump(by_alias=True, exclude_none=True),
            }
        )

    logger.info(f"Creating STAC asset {zarr_uri}/measurements...")
    zarr_asset: Asset = Asset(
        href=f"{zarr_uri}/measurements",
        media_type=ZARR_V3_MULTISCALES_MEDIA_TYPE,
        roles=["data"],
        title="Measurements",
        description="Zarr measurements group",
    )
    output_collection.add_asset(key="measurements", asset=zarr_asset)

    zarr_asset.extra_fields["bands"] = bands
    zarr_asset.extra_fields["cube:variables"] = cube_variables
    zarr_asset.extra_fields["cube:dimensions"] = {
        "time": {
            "type": "temporal",
            "extent": [
                get_temporal_extent(items)[0].isoformat().replace("+00:00", "Z"),
                get_temporal_extent(items)[1].isoformat().replace("+00:00", "Z"),
            ],
            "values": time_summary_values,
        },
        "x": {
            "type": "spatial",
            "axis": "x",
            "extent": [
                float(min(stac_catalog_dataset.x.values)),
                float(max(stac_catalog_dataset.x.values)),
            ],
        },
        "y": {
            "type": "spatial",
            "axis": "y",
            "extent": [
                float(min(stac_catalog_dataset.y.values)),
                float(max(stac_catalog_dataset.y.values)),
            ],
        },
    }

    proj_ext = ProjectionExtension.ext(zarr_asset)
    proj_ext.epsg = gbox.crs.epsg
    proj_ext.wkt2 = gbox.crs.to_wkt("WKT2_2019")
    proj_ext.shape = list(gbox.shape)
    proj_ext.transform = list(gbox.transform)
    proj_ext.bbox = spatial_bbox
    proj_ext.geometry = gbox.extent.to_crs(crs).json

    logger.info("Creating STAC Catalog for the output...")
    output_cat = Catalog(id=collection.id, description=collection.description, title=collection.title)
    raster_ext = RasterExtension.ext(zarr_asset, add_if_missing=True)
    raster_ext.bands = raster_bands
    if stac_object_type == "item":
        temporal_extent = get_temporal_extent(items)
        item_bbox = get_spatial_extent(items)
        item_geometry = items[0].geometry if items[0].geometry is not None else _bbox_to_polygon(item_bbox)
        output_item = Item(
            id=collection.id,
            geometry=item_geometry,
            bbox=item_bbox,
            datetime=temporal_extent[0],
            properties={},
        )
        output_item.stac_extensions = list(STAC_EXTENSION_URIS)
        if pystac_renders is not None:
            RenderExtension.ext(output_item, add_if_missing=True).renders = copy.deepcopy(pystac_renders)
        output_item.add_link(copy.deepcopy(store_link))
        output_item.add_asset("measurements", copy.deepcopy(zarr_asset))
        output_cat.add_item(output_item)
    else:
        output_cat.add_child(output_collection)
    output_cat.normalize_and_save(root_href=str(Path(".")), catalog_type=CatalogType.SELF_CONTAINED)

    # Remove stale opposite output type files from previous runs.
    if stac_object_type == "item":
        stale_collection = Path(collection.id, "collection.json")
        if stale_collection.exists():
            stale_collection.unlink()
    else:
        stale_item = Path(collection.id, f"{collection.id}.json")
        if stale_item.exists():
            stale_item.unlink()

    if consolidate:
        zarr_store_path = Path(collection.id, zarr_uri)
        logger.info(f"Consolidating Zarr metadata for {zarr_store_path}...")
        consolidate_zarr_store(zarr_store_path)

    logger.info("Done!")
