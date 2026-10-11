# GeoZarr Minispec Compliance

This page summarizes current compliance of `stac-zarr` outputs against:

* GeoZarr minispec: `https://eopf-explorer.github.io/data-model/geozarr-minispec/`
* STAC Zarr best practices: `https://github.com/radiantearth/stac-best-practices/blob/main/best-practices-zarr.md`

The convention schemas and specification URLs are pinned to published `v0.1` tags
in `zarr-conventions/proj`, `spatial`, and `multiscales`. These conventions are
Pilot and pre-stable; adopting them does not claim stable GeoZarr V1 conformance.
The `proj:` and `spatial:` attribute prefixes remain unchanged.

## Implemented

* Root `zarr_conventions` includes:
  - `proj`
  - `spatial`
  - `multiscales`
* Root spatial metadata:
  - `spatial:dimensions`
  - `spatial:bbox`
  - `spatial:shape`
  - `spatial:transform`
* Root multiscales metadata (GeoZarr convention v0.1 layout style):
  - `multiscales.resampling_method`
  - `multiscales.layout`
* Per-variable multiscale listing:
  - `multiscales:datasets`
* Base and overview data arrays each declare `proj` and `spatial`, with their
  own CRS, spatial dimensions, shape, transform, and pixel registration. This
  avoids relying on inheritance through intermediate groups.
* The root bbox describes outer pixel edges from the geobox extent.
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

* `multiscales` stores GeoZarr convention v0.1 layout metadata.
* `multiscales:datasets` is used for per-variable dataset paths and axes.
* Overview reducers are configurable and mapped to GeoZarr resampling names (`average`, `max`, `med`, `nearest`).

## Compliance Checks Interpretation

Running `task compliance:check:all` includes two different multiscales checks with different intent:

* `compliance:check:multiscales-layout`: strict check for this repository GeoZarr convention v0.1 layout profile.
  - Expected result: `PASS`
* `compliance:check:multiscales`: upstream `zarr-conventions/multiscales` schema compatibility report.
  - Expected result: `PASS`

This is an intentional split:

* local profile compliance is enforced by `multiscales-layout`
* upstream schema compliance is reported separately for traceability

## GeoZarr Toolkit validation

`geozarr-toolkit` is a runtime dependency. Before publishing STAC output and
consolidating metadata, the writer validates the actual root, nested groups, and
arrays with `geozarr_toolkit.validate_attrs`. Invalid metadata stops conversion.
Additional store checks enforce pinned declarations, dimension names, array
shapes, and existing pyramid paths whose spatial metadata agrees with the arrays.
CF coordinate arrays are outside the spatial convention's scope.

`task compliance:check:geozarr-toolkit` runs production-writer integration tests
that generate a small store with two overview levels, validate it, and verify
that corrupted declarations, projection/spatial metadata, and pyramid paths fail.
This check is included in `task compliance:check:all`.

Validate an existing store (read-only, ignoring stale consolidated metadata):

```bash
task compliance:check:store STORE=/absolute/path/to/output.zarr
```

The individual upstream JSON Schema checks use the same pinned `v0.1` schema
URLs. They check representative payloads; the Toolkit integration tests and store
command check actual stores. `multiscales:datasets` is a local discovery attribute,
not part of the upstream multiscales convention.
