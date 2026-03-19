# Input STAC Requirements

## Mandatory use of the Item Assets Extension

The tooling that reads a STAC Catalog and produces STAC/Zarr outputs expects the input STAC Catalog to contain a STAC Collection with the Item Assets extension defined.

The `item_assets` definitions are used as the authoritative source for deriving the measurements written to the output Zarr store (native Zarr v3 or Zarr v2 following EOPF conventions).

Note: Collections without item_assets are considered invalid inputs for this tool.

## Why item_assets is required

The conversion process produces a Zarr layout of the form:

```
data.zarr/
└── measurements/
    ├── <measurement-1>/
    ├── <measurement-2>/
    └── ...
```

Each Zarr measurement group is derived from a corresponding Item Asset definition in the Collection.

The Item Assets extension provides:

* The canonical list of measurements to materialize
* Stable measurement identifiers (asset keys)
* Semantic metadata (title, description, roles)
* Media type and band definitions

This avoids relying on:

* implicit inspection of Items
* asset presence heuristics
* dataset-specific assumptions

## Expected Collection structure

The input STAC Collection **MUST**:

* Declare the Item Assets extension
* Define an `item_assets` object
* Include one entry per measurement to be written

Minimal example:

```json
{
  "type": "Collection",
  "stac_version": "1.1.0",

  "stac_extensions": [
    "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json"
  ],

  "item_assets": {
    "water-bodies": {
      "title": "Water Bodies",
      "description": "Water bodies classification",
      "roles": ["data"],
      "type": "application/vnd.zarr; version=3",
      "bands": [
        {
          "name": "water-bodies",
          "description": "Water bodies classification"
        }
      ]
    },
    "water-bodies-confidence": {
      "title": "Water Bodies Confidence",
      "description": "Confidence of water bodies detection",
      "roles": ["data"],
      "type": "application/vnd.zarr; version=3"
    }
  }
}
```

## How item_assets is used by the tool

For each entry in collection.item_assets:

| Item Assets field | Usage in Zarr output |
|-------------------|----------------------|
| Asset key | Name of the Zarr measurement group |
| `title` | Zarr group attribute (`title`) |
| `description` | Zarr group attribute (`description`) |
| `bands` | Variables created under the measurement group |
| `roles` | Informational (not mapped to storage layout) |
| `type` | Validation of expected data model |

The tool does not infer measurements from Items.
Only measurements explicitly declared in item_assets are materialized.

## Relationship with Items

* Items are used only as a source of data
* Items MAY contain additional assets
* Assets not declared in item_assets are ignored

This allows:

* heterogeneous Items
* sparse or partial Item coverage
* future Item evolution without breaking the Zarr layout

## Validation behavior

If any of the following conditions are met, the tool fails fast:

* item_assets is missing
* an Item Asset key is not found in at least one Item
* required band variables cannot be resolved

This ensures the output Zarr store is:

* deterministic
* schema-driven
* reproducible
* aligned with the STAC Zarr Best Practices

## Rationale (design choice)

Using item_assets as the measurement contract:

* aligns with STAC best practices
* avoids Item-level duplication
* supports Collection-only data models
* cleanly maps to EOPF `measurements/*` layout
* works equally well for native and virtual Zarr stores

This approach treats the STAC Collection as the data model and Items as data carriers, which is consistent with datacube-oriented workflows.

## GeoZarr Conventions Implemented in Zarr v3 Output

The `stac-zarr` tool writes native Zarr v3 and annotates the root group with conventions metadata aligned with the GeoZarr conventions registry.

Implemented conventions in `root.attrs["zarr_conventions"]`:

* `proj:` (geo-proj convention)
* `spatial:` (spatial convention)
* `multiscales` (multiscales convention)

### Root-level convention attributes

The output Zarr root includes:

* `proj:code`
* `spatial:dimensions`
* `spatial:bbox`
* `spatial:shape`
* `spatial:transform`
* `multiscales`
* `multiscales:datasets`

These attributes are derived from the loaded datacube geobox and are consistent with the STAC Projection and Datacube metadata written in the output Collection.

## Multiscale Layout Implemented

For each measurement declared in `collection.item_assets`, the writer produces:

```text
<collection-id>.zarr/
├── measurements/
│   ├── <measurement>          # base level (level 0)
│   ├── time
│   ├── x
│   ├── y
│   └── spatial_ref
└── measurements_overviews/
    └── <measurement>/
        ├── 1/
        │   ├── <measurement>  # overview level 1 data array
        │   ├── time
        │   ├── x
        │   ├── y
        │   └── spatial_ref
        ├── 2/
        │   └── ...
        └── ...
```

The root `multiscales` attribute uses TileMatrixSet-based metadata (`resampling_method`, `tile_matrix_set`), and `multiscales:datasets` lists per-measurement dataset paths and axes.

## Overview Downsampling Configuration

The tool supports overview generation with configurable reducers by variable type.

CLI options:

* `--overview-levels` (default: `2`)
* `--continuous-overview-reducer` (default: `mean`)
* `--categorical-overview-reducer` (default: `nearest`)

Supported reducers:

* `mean`
* `max`
* `median`
* `nearest`

Variable typing used by the implementation:

* floating and complex dtypes: `continuous`
* all other dtypes: `categorical`

Overview metadata includes:

* `overview:reducer`
* `overview:variable_type`
* `downsampling_factor`

## GeoZarr Minispec Compliance Notes

Reference:
`https://eopf-explorer.github.io/data-model/geozarr-minispec/`

Implemented in this writer:

* convention metadata (`zarr_conventions`) for `proj:`, `spatial:`, `multiscales`
* `spatial:*` root metadata and TileMatrixSet-style `multiscales`
* CF-style dataset members (`time`, `x`, `y`, `spatial_ref`)
* data-array attributes: `grid_mapping`, `coordinates`
* dataset-level validation of coordinate and grid-mapping references

Current limitations:

* root projection metadata is currently `proj:code` only
* `tile_matrix_limits` is not yet emitted

## CWL Workflow Parameters

The producer workflow exposes top-level STAC discovery fields in `app-water-bodies.cwl`:

* `stac_api_endpoint`
* `collection`
* `bbox`
* `start-datetime`
* `end-datetime`
* `limit`
* `max-items`
* `filter-lang`
* `filter`

These are normalized internally into `STACSearchSettings` before the `discovery` step.

The producer workflow also exposes Zarr overview controls:

* `overview_levels`
* `continuous_overview_reducer`
* `categorical_overview_reducer`

These are passed to the `stac-zarr` CommandLineTool as:

* `--overview-levels`
* `--continuous-overview-reducer`
* `--categorical-overview-reducer`

## `stac-eopf-product` Interface (Internal in CWL)

The producer workflow includes an internal `stac-eopf-product` step that is currently fed from `stac-collection/temp_stac_catalog`.

Its CommandLineTool interface supports:

* `--stac-catalog`
* `--resolution` (optional)
* `--chunks` (`manual|auto`)
* `--chunk-x`
* `--chunk-y`
* `--chunk-time`

These are defined at `cwl-workflow/app-water-bodies.cwl#stac-eopf-product` and default to:

* `resolution: null`
* `chunks: manual`
* `chunk-x: 512`
* `chunk-y: 512`
* `chunk-time: 1`

Input contract for this step:

* Collection `item_assets` is mandatory
* measurement keys are derived from `collection.item_assets`
* each input Item must include all declared measurement keys
