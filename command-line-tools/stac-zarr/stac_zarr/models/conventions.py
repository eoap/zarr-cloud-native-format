from typing import Literal

from stac_zarr.models.common import ZarrConventionMetadata


class SpatialConventionMetadata(ZarrConventionMetadata):
    uuid: Literal["689b58e2-cf7b-45e0-9fff-9cfc0883d6b4"] = "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4"
    name: Literal["spatial:"] = "spatial:"
    schema_url: Literal[
        "https://raw.githubusercontent.com/zarr-conventions/spatial/refs/tags/v1/schema.json"
    ] = "https://raw.githubusercontent.com/zarr-conventions/spatial/refs/tags/v1/schema.json"
    spec_url: Literal["https://github.com/zarr-conventions/spatial/blob/v1/README.md"] = (
        "https://github.com/zarr-conventions/spatial/blob/v1/README.md"
    )
    description: Literal["Spatial coordinate information"] = "Spatial coordinate information"


class GeoProjConventionMetadata(ZarrConventionMetadata):
    uuid: Literal["f17cb550-5864-4468-aeb7-f3180cfb622f"] = "f17cb550-5864-4468-aeb7-f3180cfb622f"
    name: Literal["proj:"] = "proj:"
    schema_url: Literal[
        "https://raw.githubusercontent.com/zarr-experimental/geo-proj/refs/tags/v1/schema.json"
    ] = "https://raw.githubusercontent.com/zarr-experimental/geo-proj/refs/tags/v1/schema.json"
    spec_url: Literal["https://github.com/zarr-experimental/geo-proj/blob/v1/README.md"] = (
        "https://github.com/zarr-experimental/geo-proj/blob/v1/README.md"
    )
    description: Literal[
        "Coordinate reference system information for geospatial data"
    ] = "Coordinate reference system information for geospatial data"


class MultiscalesConventionMetadata(ZarrConventionMetadata):
    uuid: Literal["d35379db-88df-4056-af3a-620245f8e347"] = "d35379db-88df-4056-af3a-620245f8e347"
    name: Literal["multiscales"] = "multiscales"
    schema_url: Literal[
        "https://raw.githubusercontent.com/zarr-conventions/multiscales/refs/tags/v1/schema.json"
    ] = "https://raw.githubusercontent.com/zarr-conventions/multiscales/refs/tags/v1/schema.json"
    spec_url: Literal["https://github.com/zarr-conventions/multiscales/blob/v1/README.md"] = (
        "https://github.com/zarr-conventions/multiscales/blob/v1/README.md"
    )
    description: Literal["Multiscale layout of zarr datasets"] = "Multiscale layout of zarr datasets"
