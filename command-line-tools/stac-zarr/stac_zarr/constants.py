from typing import Dict, List

GEO_PROJ_CONVENTION: Dict[str, str] = {
    "schema_url": "https://raw.githubusercontent.com/zarr-experimental/geo-proj/main/schema.json",
    "spec_url": "https://github.com/zarr-experimental/geo-proj/blob/v1/README.md",
    "uuid": "f17cb550-5864-4468-aeb7-f3180cfb622f",
    "name": "proj:",
    "description": "Coordinate reference system information for geospatial data",
}

SPATIAL_CONVENTION: Dict[str, str] = {
    "schema_url": "https://raw.githubusercontent.com/zarr-conventions/spatial/main/schema.json",
    "spec_url": "https://github.com/zarr-conventions/spatial/blob/v1/README.md",
    "uuid": "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4",
    "name": "spatial:",
    "description": "Spatial coordinate information",
}

MULTISCALES_CONVENTION: Dict[str, str] = {
    "schema_url": "https://raw.githubusercontent.com/zarr-conventions/multiscales/main/schema.json",
    "spec_url": "https://github.com/zarr-conventions/multiscales/blob/v1/README.md",
    "uuid": "d35379db-88df-4056-af3a-620245f8e347",
    "name": "multiscales",
    "description": "Multiscale layout of zarr datasets",
}

OVERVIEW_REDUCERS = ("mean", "max", "median", "nearest")
ZARR_V3_MULTISCALES_MEDIA_TYPE = "application/vnd.zarr; version=3; profile=multiscales"
STAC_EXTENSION_URIS: List[str] = [
    "https://stac-extensions.github.io/projection/v2.0.0/schema.json",
    "https://stac-extensions.github.io/raster/v2.0.0/schema.json",
    "https://stac-extensions.github.io/datacube/v2.2.0/schema.json",
]
