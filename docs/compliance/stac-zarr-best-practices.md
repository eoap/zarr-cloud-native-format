# TL;DR — STAC Zarr Best Practices

* Use STAC Items for single scenes or time slices, and STAC Collections for datasets spanning multiple times/regions. Each Item or Collection may reference one Zarr store.
* One STAC asset = one Zarr group (not individual arrays). Arrays and subgroups live inside the asset’s Zarr hierarchy.
* Always link the Zarr store using `rel: store`, pointing to the root of the (native or virtual) Zarr store. All Zarr assets are assumed to live under this store.
* Use the correct Zarr media type with version:
  - `application/vnd.zarr; version=2`
  - `application/vnd.zarr; version=3`
* Add `profile=multiscales` when publishing multiscale Zarr assets.
* Do not expose arrays as assets.
* Expose bands via the bands array:
  - One variable = one band → name = variable name
  - One variable, many bands → encode band selection in name
  - Multiscales → bands are resolution-agnostic; resolution is inferred from the Zarr layout
* Asset href always points to a Zarr group, never directly to an array.
* Clients access arrays by path-joining asset.href + band.name.
* For multiresolution data:
  - Either expose one asset per resolution, or
  - A single multiscales asset pointing to the parent group (preferred when resolutions are tightly coupled)
* Use STAC extensions consistently:
  - Datacube: describe variables and dimensions (cube:variables, cube:dimensions)
  - Projection: spatial reference (proj:*)
  - Raster: raster properties (resolution, nodata, dtype)
  - CF: climate/forecast semantics (cf:standard_name, units, etc.)
* Virtual Zarr stores (Kerchunk, VirtualiZarr, icechunk):
  - Treat them like native Zarr
  - `rel: store` points to the reference/entrypoint
  - Assets may carry role `"virtual"`
  - Source files may be referenced separately with role "source"
* Link Templates MAY be used to advertise variable-level access without enumerating arrays as assets.

In short: 

* STAC describes what is in the Zarr store, not how to traverse it.
* Zarr handles structure; STAC handles discovery, semantics, and access hints.

## Current Implementation in This Repository

The `stac-zarr` tool implements the following conventions and metadata patterns for Zarr v3 outputs.

### STAC-side implementation

* `rel: store` link on the output Collection pointing to `<collection-id>.zarr`
* `measurements` STAC asset pointing to `<collection-id>.zarr/measurements`
* Zarr media type includes `profile=multiscales`
* Datacube metadata at asset level using:
  - `cube:variables`
  - `cube:dimensions`
* Projection metadata at asset level (`proj:*`)
* Raster metadata at asset level (`raster:bands`)
* STAC extension URIs pinned to:
  - projection `v2.0.0`
  - raster `v2.0.0`
  - datacube `v2.2.0`

### Zarr-side implementation

Root group attributes include:

* `zarr_conventions`
* exactly one of projection representations:
  - `proj:projjson` (preferred)
  - `proj:wkt2` (fallback)
  - `proj:code` (fallback)
* `spatial:dimensions`
* `spatial:bbox`
* `spatial:shape`
* `spatial:transform`
* `multiscales`

Registered conventions in `zarr_conventions`:

* `proj:`
* `spatial:`
* `multiscales`

### Multiscales implementation

For each measurement:

* Base level written to `measurements/<measurement>`
* Overview levels written to `measurements_overviews/<measurement>/<level>/<measurement>`
* Root `multiscales` uses TileMatrixSet metadata:
  - `resampling_method`
  - `tile_matrix_set`
* Per-measurement dataset listing is exposed in `multiscales:datasets`

Overview generation controls:

* `--overview-levels`
* `--continuous-overview-reducer`
* `--categorical-overview-reducer`

Reducers supported:

* `mean`
* `max`
* `median`
* `nearest`

### CF dataset semantics

For base and overview datasets, data arrays include:

* `grid_mapping = "spatial_ref"`
* `coordinates = "time y x"`

Dataset groups include coordinate members:

* `time` (CF-style numeric time, seconds since epoch)
* `x`
* `y`
* `spatial_ref`

The writer validates:

* coordinate references and dimension-shape consistency
* `grid_mapping` references to existing dataset members

## GeoZarr Minispec Compliance (Current)

Reference:
`https://eopf-explorer.github.io/data-model/geozarr-minispec/`

Implemented:

* `zarr_conventions` includes `proj:`, `spatial:`, `multiscales`
* `spatial:*` root attributes (`dimensions`, `bbox`, `shape`, `transform`)
* TileMatrixSet-style `multiscales` object (`resampling_method`, `tile_matrix_set`)
* `multiscales.tile_matrix_limits` emitted per level
* multiscale data levels with explicit dataset paths
* CF-style dataset members and `grid_mapping` linkage checks

Partially implemented:

* `tile_matrix_limits` currently assumes full matrix coverage per level

Forward work items:

* refine `tile_matrix_limits` for partial coverage scenarios
* extend reducer-to-resampling mapping if additional methods are introduced

### Compliance Check Notes

When running `task compliance:check:all`:

* `compliance:check:multiscales-tms` is the authoritative strict check for the emitted TileMatrixSet profile and is expected to pass.
* `compliance:check:multiscales` validates against upstream layout-oriented `zarr-conventions/multiscales` schema and is expected to fail with the current TileMatrixSet representation.

This behavior is expected and does not indicate a regression for the selected GeoZarr/TiTiler-oriented profile.

### Measurement contract

The implementation is Collection-driven:

* `collection.item_assets` is mandatory
* measurement keys are sourced from `collection.item_assets`
* each input Item must include all declared measurement keys
* no measurement inference from Item-only extra assets
