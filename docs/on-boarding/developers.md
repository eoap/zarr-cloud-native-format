# Developer Onboarding

## Goal

Contribute safely to the CLI tools and CWL workflows, especially `stac-zarr`.

## Repository map

* `command-line-tools/stac-collection/`: STAC packaging step for NDWI/Otsu outputs
* `command-line-tools/stac-zarr/`: Zarr v3 + STAC writer
* `command-line-tools/occurrence/`: consumer tool (reads Zarr STAC output and derives occurrence)
* `command-line-tools/stac-eopf-product/`: EOPF-style Zarr output
* `cwl-workflow/`: producer and consumer workflow definitions
* `docs/`: MkDocs content and notebook-backed walkthroughs

## Local setup (uv + Task, recommended)

```bash
uv sync
```

Useful commands:

```bash
task test:unit:scoped
task cwl:run:producer
task cwl:test:e2e
task containers:build:producer
```

## Local setup (pip editable, alternative)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e command-line-tools/stac-collection
pip install -e command-line-tools/stac-zarr
pip install -e command-line-tools/occurrence
pip install -e command-line-tools/stac-eopf-product
```

## Common checks

```bash
task test:unit:scoped
task cwl:check:release
```

## `stac-zarr` implementation contract

`stac-zarr` is Collection-driven:

* `collection.item_assets` is required
* measurement list is derived from `collection.item_assets`
* each input Item must contain all declared measurement keys

`stac-zarr` also writes:

* STAC `rel: store` and asset-level metadata (`cube:*`, `proj:*`, `raster:*`)
* Zarr v3 root conventions metadata (`zarr_conventions`, `multiscales`, `proj:*`, `spatial:*`)
* overview pyramids under `measurements_overviews/`

Overview controls:

* `--overview-levels`
* `--continuous-overview-reducer` (`mean|max|median|nearest`)
* `--categorical-overview-reducer` (`mean|max|median|nearest`)

When changing CLI options, update:

* `cwl-workflow/app-water-bodies.cwl`
* docs pages (`docs/input-stac.md`, `docs/compliance/stac-zarr-best-practices.md`)

## Regenerating Pydantic convention models

`stac-zarr` can regenerate schema-derived Pydantic models (instead of hand-editing) with:

```bash
task models:generate:all
```

Or run individually:

```bash
task models:generate:spatial
task models:generate:geo-proj
task models:generate:multiscales
```

Generated files are written to:

* `command-line-tools/stac-zarr/stac_zarr/models/generated/`

Notes:

* `geo-proj` schema is modular, so generation creates a package:
  * `command-line-tools/stac-zarr/stac_zarr/models/generated/geo_proj/__init__.py`
  * `command-line-tools/stac-zarr/stac_zarr/models/generated/geo_proj/_internal.py`
  * `command-line-tools/stac-zarr/stac_zarr/models/generated/geo_proj/projjson.py`
* `spatial` and `multiscales` currently generate single modules:
  * `.../generated/spatial.py`
  * `.../generated/multiscales.py`
* Runtime `stac-zarr` uses generated convention/spatial models; legacy hand-written models were removed.
