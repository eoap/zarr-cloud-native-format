import os
from pathlib import Path
from typing import Any, Dict, List

import dask.array
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
from xarray import DataArray, Dataset
from zarr.types import AnyArray

from stac_zarr.cf import validate_dataset_group, write_cf_dataset_members
from stac_zarr.constants import (
    STAC_EXTENSION_URIS,
    ZARR_V3_MULTISCALES_MEDIA_TYPE,
)
from stac_zarr.models.conventions import (
    GeoProjConventionMetadata,
    MultiscalesConventionMetadata,
    SpatialConventionMetadata,
)
from stac_zarr.models.multiscales import (
    Multiscales,
    MultiscalesDatasetEntry,
    TileMatrixSet,
)
from stac_zarr.models.spatial import Spatial
from stac_zarr.contract import (
    extract_crs,
    get_measurement_keys,
    get_spatial_extent,
    get_temporal_extent,
    validate_items_have_measurements,
)
from stac_zarr.multiscales import build_tile_matrix_set
from stac_zarr.reducers import downsample_2x, get_variable_type, to_resampling_method


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
    output_collection.stac_extensions = STAC_EXTENSION_URIS

    zarr_uri = f"{collection.id}.zarr"
    output_collection.add_link(
        Link(
            rel="store",
            target=zarr_uri,
            media_type=ZARR_V3_MULTISCALES_MEDIA_TYPE,
            title=f"Zarr store for {collection.title}",
        )
    )

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
    overviews_measurements_grp = root.require_group(f"{measurement_name}_overviews")

    bands = []
    cube_variables = {}
    raster_bands = []
    multiscales_entries: List[Dict[str, Any]] = []
    multiscales_level_shapes: List[List[int]] = []
    default_resampling_method = to_resampling_method(categorical_overview_reducer)
    crs_wkt = gbox.crs.to_wkt("WKT2_2019")

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

    multiscales_model = Multiscales(
        resampling_method=default_resampling_method,
        tile_matrix_set=TileMatrixSet.model_validate(tile_matrix_set),
    )
    multiscales_datasets_model = [
        MultiscalesDatasetEntry.model_validate(entry)
        for entry in multiscales_entries
    ]
    spatial_model = Spatial(
        **{
            "spatial:dimensions": ["y", "x"],
            "spatial:bbox": spatial_bbox,
            "spatial:shape": list(gbox.shape),
            "spatial:transform": affine_6,
        }
    )

    root.attrs.update(
        {
            "zarr_conventions": [
                MultiscalesConventionMetadata().model_dump(),
                GeoProjConventionMetadata().model_dump(),
                SpatialConventionMetadata().model_dump(),
            ],
            "multiscales": multiscales_model.model_dump(by_alias=True, exclude_none=True),
            "multiscales:datasets": [
                entry.model_dump(by_alias=True, exclude_none=True)
                for entry in multiscales_datasets_model
            ],
            "proj:code": proj_code,
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
    output_cat.add_child(output_collection)
    output_cat.normalize_and_save(root_href=str(Path(".")), catalog_type=CatalogType.SELF_CONTAINED)

    logger.info("Done!")
