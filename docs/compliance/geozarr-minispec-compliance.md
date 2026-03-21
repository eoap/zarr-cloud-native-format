# GeoZarr Minispec Compliance

This page summarizes current compliance of `stac-zarr` outputs against:

* GeoZarr minispec: `https://eopf-explorer.github.io/data-model/geozarr-minispec/`
* STAC Zarr best practices: `https://github.com/radiantearth/stac-best-practices/blob/main/best-practices-zarr.md`

## Implemented

* Root `zarr_conventions` includes:
  - `proj:`
  - `spatial:`
  - `multiscales`
* Root spatial metadata:
  - `spatial:dimensions`
  - `spatial:bbox`
  - `spatial:shape`
  - `spatial:transform`
* Root multiscales metadata (GeoZarr v1 layout style):
  - `multiscales.resampling_method`
  - `multiscales.layout`
* Per-variable multiscale listing:
  - `multiscales:datasets`
* Base and overview data arrays include CF linkage attributes:
  - `grid_mapping = "spatial_ref"`
  - `coordinates = "time y x"`
* Base and overview dataset groups include CF members:
  - `time`
  - `x`
  - `y`
  - `spatial_ref`
* Dataset-level validation during writing:
  - coordinate references and dimension-shape checks
  - `grid_mapping` member reference checks
* STAC-side metadata patterns:
  - `rel: store`
  - Zarr media type with `profile=multiscales`
  - projection/raster/datacube extension metadata
  - STAC extension URIs pinned to projection `v2.0.0`, raster `v2.0.0`, datacube `v2.2.0`
* Root projection metadata emitted with strict one-of semantics:
  - `proj:projjson` preferred
  - `proj:wkt2` fallback
  - `proj:code` fallback

## Known Design Choices

* `multiscales` stores GeoZarr v1 layout metadata.
* `multiscales:datasets` is used for per-variable dataset paths and axes.
* Overview reducers are configurable and mapped to GeoZarr resampling names (`average`, `max`, `med`, `nearest`).

## Compliance Checks Interpretation

Running `task compliance:check:all` includes two different multiscales checks with different intent:

* `compliance:check:multiscales-layout`: strict check for this repository GeoZarr v1 layout profile.
  - Expected result: `PASS`
* `compliance:check:multiscales`: upstream `zarr-conventions/multiscales` schema compatibility report.
  - Expected result: `PASS`

This is an intentional split:

* local profile compliance is enforced by `multiscales-layout`
* upstream schema compliance is reported separately for traceability

## Forward Work Items

* Add a dedicated compliance test that validates emitted root attributes and dataset members from a generated sample.
