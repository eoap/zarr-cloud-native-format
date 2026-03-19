# Onboarding Guide

This guide is for three audiences:

* developers contributing code
* EOAP users running the application package
* maintainers operating releases and documentation

## 1) Developers

### Goal

Contribute safely to the CLI tools and CWL workflows, especially `stac-zarr`.

### Repository map

* `command-line-tools/stac-zarr/`: Zarr v3 + STAC writer
* `command-line-tools/occurrence/`: consumer tool (reads Zarr STAC output and derives occurrence)
* `command-line-tools/stac-eopf-product/`: EOPF-style Zarr output
* `cwl-workflow/`: producer and consumer workflow definitions
* `docs/`: MkDocs content and notebook-backed walkthroughs

### Local setup (uv + Task, recommended)

This repository is now documented with `uv` and `task` as the primary local workflow.

At repo root:

```bash
uv sync
```

Useful task commands:

```bash
task test:unit:scoped
task cwl:run:producer
task cwl:test:e2e
task containers:build:producer
```

### Local setup (pip editable, alternative)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e command-line-tools/stac-zarr
pip install -e command-line-tools/occurrence
pip install -e command-line-tools/stac-eopf-product
```

### Common checks

```bash
task test:unit:scoped
```

### `stac-zarr` implementation contract

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

When changing CLI options, update both:

* `cwl-workflow/app-water-bodies.cwl`
* docs pages (`docs/input-stac.md`, `docs/stac-zarr-best-practices.md`)

## 2) EOAP Users

### Goal

Run the producer and consumer workflows with minimal setup.

### What you need

* CWL runner (for example `cwltool`)
* container runtime supported by your environment
* access to the STAC API endpoint and search parameters

### Primary workflow files

* Producer: `cwl-workflow/app-water-bodies.cwl#water-bodies`
* Consumer: `cwl-workflow/app-water-bodies-occurrence.cwl#water-bodies-occurrence`

### Producer parameters to know

The producer takes top-level discovery inputs (instead of a nested `search_request` object):

* `stac_api_endpoint` (object with `url` and optional `headers`)
* `collection` (STAC collection id)
* `bbox` (`[minx, miny, maxx, maxy]`)
* `start-datetime` and `end-datetime` (optional)
* `limit` and `max-items`
* `filter-lang` and `filter` (optional)

Processing inputs:

* `bands` (default `["green", "nir"]`)

Zarr overview controls:

* `overview_levels` (default `2`)
* `continuous_overview_reducer` (default `"mean"`)
* `categorical_overview_reducer` (default `"nearest"`)

Internal `stac-eopf-product` controls in the producer CWL step:

* `resolution` (default `null`)
* `chunks` (default `manual`)
* `chunk_x` (default `512`)
* `chunk_y` (default `512`)
* `chunk_time` (default `1`)

Example producer job:

```yaml
stac_api_endpoint:
  headers: []
  url: https://earth-search.aws.element84.com/v1/
collection: sentinel-2-l2a
bbox:
  - -121.399
  - 39.834
  - -120.74
  - 40.472
start-datetime: "2021-06-01T00:00:00"
end-datetime: "2021-08-01T23:59:59"
limit: 20
max-items: 10
filter-lang: null
filter: null
bands:
  - green
  - nir
overview_levels: 2
continuous_overview_reducer: mean
categorical_overview_reducer: nearest
```

Use the labs and notebooks for end-to-end examples:

* `docs/cwl-workflows/producer.ipynb`
* `docs/cwl-workflows/consumer.ipynb`
* `docs/exploitation.ipynb`

## 3) Maintainers

### Goal

Keep code, workflows, containers, and docs aligned.

### Alignment checklist

For every user-visible change:

* CLI option changes in Python tools are mirrored in CWL inputs
* docs reflect current behavior and defaults
* examples/notebooks are still coherent with current interfaces

### High-risk drift points

* `stac-zarr` CLI flags vs `app-water-bodies.cwl` `stac-zarr` tool inputs
* `stac-eopf-product` CLI flags vs `app-water-bodies.cwl` `stac-eopf-product` tool inputs
* STAC/Zarr conventions described in docs vs emitted metadata
* workflow output expectations in consumer tooling

### Release hygiene

Before publishing:

* run syntax checks on edited Python modules
* verify CWL fields and defaults for new parameters
* verify MkDocs navigation includes new pages
* review docs for behavior/default mismatches

### Ownership recommendation

Treat these artifacts as one change set whenever touching Zarr output behavior:

* `command-line-tools/stac-zarr/stac_zarr/app.py`
* `cwl-workflow/app-water-bodies.cwl`
* `docs/input-stac.md`
* `docs/stac-zarr-best-practices.md`
* this onboarding page
