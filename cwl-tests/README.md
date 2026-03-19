# CWL End-to-End Tests

This folder contains `cwltest` suites for workflows in `cwl-workflow/`.

## Scope

Current suite:

* producer workflow end-to-end test for `cwl-workflow/app-water-bodies.cwl#water-bodies`

The test validates that the workflow completes and returns the expected top-level outputs as `Directory` objects:

* `zarr_stac_catalog`
* `stac_catalog`
* `eopf_product_stac_catalog`

## Prerequisites

* `cwltool`
* `cwltest`
* container runtime available to `cwltool`
* network access to remote STAC API and remote CWL/schema/container resources used by the workflow

Install example:

```bash
pip install cwltool cwltest
```

## Run

From repository root:

```bash
task cwl:test:e2e
```

Or directly:

```bash
cwltest \
  --test tests/app-water-bodies-e2e.yml \
  --basedir cwl-tests \
  --tool cwltool \
  --timeout 3600
```

## Notes

* This is a real end-to-end test, not a mocked test.
* Runtime and stability depend on external service availability.
* Use `--tags` / `--exclude-tags` in `cwltest` to select subsets when adding more tests.
* Job inputs follow the new producer interface in `jobs/producer-job.yml` (`collection`, `bbox`, `start-datetime`, `end-datetime`, `limit`, `max-items`, `filter-lang`, `filter`, `stac_api_endpoint`).
