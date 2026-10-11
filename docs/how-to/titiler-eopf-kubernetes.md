# Publish GeoZarr to S3 and display it on Kubernetes

The development-platform deployment runs SeaweedFS, TiTiler-EOPF **0.12.2**,
a `stac-fastapi-geoparquet` API and the HTML client alongside the PDE editor.
It uses the upstream TiTiler image without the historical local-reader patch.

## Producer and stage-out

Use `cwl-tests/jobs/producer-job-item.yml`: TiTiler resolves **STAC Item assets**.
The producer now points its measurements asset to the complete `.zarr` store,
and its multiscale layout points to dataset groups with a shared base group.
Root metadata and all measurement overviews are available to the reader.

```sh
task containers:build:stage-out
task cwl:wrap:producer
# An explicit job supplies the normal producer inputs plus the stage-out inputs.
task cwl:run:producer:s3 JOB=/path/to/private-job.yml
```

The wrapper uses eoap-cwlwrap 0.32.0 and cwl-loader 0.27.0, serializes an explicit
CWL v1.2 graph and embeds the necessary schemas. It only stages the final
`zarr_stac_catalog`; intermediate catalogs stay internal. Original source CWL
imports remain unchanged. No packing command is used.

The extra inputs are `s3_bucket`, `sub_path`, `aws_access_key_id`,
`aws_secret_access_key`, `region_name` and `endpoint_url`. Do not commit private
credentials. Set `STAGE_OUT_IMAGE` when wrapping to select your locally built or
published updated mastering image. The historical released stage image does not
support recursive Zarr uploads.

The reusable mastering stage-out uploads directories recursively. A subgroup
asset causes the entire enclosing Zarr store to be uploaded, including root
metadata and sibling overviews. It publishes rewritten STAC documents after
asset upload succeeds and preserves the original local catalog. The wrapper
returns an S3 catalog URI as `zarr_stac_catalog.value`.

## Development-platform publication

In `dev-platform-eoap/zarr-cloud-native-format`:

```sh
task deploy
task viewer:publish DATA_ROOT=/workspace/zarr-cloud-native-format/runs/my-output
# Local CWL results are staged; an already staged URI is indexed directly.
task viewer:publish RESULTS=/workspace/zarr-cloud-native-format/cwl-tests/results-s3.json
task test:viewer
task viewer
```

The platform publication task wraps a completed-output workflow and runs its
stage-out with the PDE's isolated Calrissian environment. It obtains the image
and S3 settings from Kubernetes configuration, then generates a GeoParquet index
from the S3-published Items. The index preserves S3 asset URLs and render/time
metadata. A portable `items.parquet` is uploaded beside the catalog in S3;
the API queries an atomic local mirror on the shared PVC to avoid requiring
DuckDB's own custom-S3 endpoint configuration. No database is deployed.

The API exposes standard collection/item routes. TiTiler resolves an item asset
through that API, then reads Zarr arrays **directly from SeaweedFS**. The client
uses `/stac/` for metadata and `/api/` for TiTiler, both through its same-origin
proxy. Its variable resolver handles root variable names such as `ndwi`.

`task test:viewer:fixture` creates two local raster dates, runs the actual module
writer and GeoZarr validation, executes the wrapped stage-out in a real
Kubernetes pod, publishes the index and verifies actual S3-backed tiles and time
selection. It switches the active collection to that fixture; publish your
learning outputs afterwards. Full remote EO product processing is a separate
validation path.
