# GeoZarr Minispec Compliance

This page summarizes current compliance of `stac-zarr` outputs against:

* GeoZarr minispec: `https://eopf-explorer.github.io/data-model/geozarr-minispec/`
* STAC Zarr best practices: `https://github.com/radiantearth/stac-best-practices/blob/main/best-practices-zarr.md`

## Implemented

* Root `zarr_conventions` includes:
  * `proj:`
  * `spatial:`
  * `multiscales`
* Root spatial metadata:
  * `spatial:dimensions`
  * `spatial:bbox`
  * `spatial:shape`
  * `spatial:transform`
* Root multiscales metadata (TileMatrixSet style):
  * `multiscales.resampling_method`
  * `multiscales.tile_matrix_set`
* Per-variable multiscale listing:
  * `multiscales:datasets`
* Base and overview data arrays include CF linkage attributes:
  * `grid_mapping = "spatial_ref"`
  * `coordinates = "time y x"`
* Base and overview dataset groups include CF members:
  * `time`
  * `x`
  * `y`
  * `spatial_ref`
* Dataset-level validation during writing:
  * coordinate references and dimension-shape checks
  * `grid_mapping` member reference checks
* STAC-side metadata patterns:
  * `rel: store`
  * Zarr media type with `profile=multiscales`
  * projection/raster/datacube extension metadata
  * STAC extension URIs pinned to projection `v2.0.0`, raster `v2.0.0`, datacube `v2.2.0`

## Partially Implemented

* Root projection metadata currently provides `proj:code`; root `proj:wkt2` / `proj:projjson` is not yet emitted.
* `multiscales.tile_matrix_limits` is not currently emitted.

## Known Design Choices

* `multiscales` stores TileMatrixSet-oriented metadata.
* `multiscales:datasets` is used for per-variable dataset paths and axes.
* Overview reducers are configurable and mapped to GeoZarr resampling names (`average`, `max`, `med`, `nearest`).

## Suggested Next Steps

1. Add optional root-level `proj:wkt2` and/or `proj:projjson`.
2. Add optional `tile_matrix_limits`.
3. Add a dedicated compliance test that validates emitted root attrs and dataset members from a generated sample.
