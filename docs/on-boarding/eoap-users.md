# EOAP Users Onboarding

## Goal

Run the producer and consumer workflows with minimal setup.

## What you need

* CWL runner (for example `cwltool`)
* container runtime supported by your environment
* access to the STAC API endpoint and search parameters

## Primary workflow files

* Producer: `cwl-workflow/app-water-bodies.cwl#water-bodies`
* Consumer: `cwl-workflow/app-water-bodies-occurrence.cwl#water-bodies-occurrence`

## Producer parameters

Top-level discovery inputs:

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

Internal `stac-eopf-product` controls in producer CWL:

* `resolution` (default `null`)
* `chunks` (default `manual`)
* `chunk_x` (default `512`)
* `chunk_y` (default `512`)
* `chunk_time` (default `1`)

## Example producer job

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

## Useful commands

```bash
task cwl:run:producer
task cwl:test:e2e
```

## End-to-end examples

* `docs/cwl-workflows/producer.ipynb`
* `docs/cwl-workflows/consumer.ipynb`
* `docs/exploitation.ipynb`
