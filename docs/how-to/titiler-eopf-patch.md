# How-To: TiTiler-EOPF Local Patch for Time Selection

This repository includes a local patch image for `ghcr.io/eopf-explorer/titiler-eopf:main` to fix time selection issues seen with `sel=time`.

## Known issue details (upstream image)

Observed on `ghcr.io/eopf-explorer/titiler-eopf:main`:

* `sel=time=<ISO-with-colons>&sel_method=nearest` is rejected by query validation (`422`).
* Alternative selector forms can pass validation but fail later at selection time (`500`), for example with:
  * `TypeError: dtype=datetime64[Y] is not supported. Supported resolutions are 's', 'ms', 'us', and 'ns'`

Typical failing forms:

```text
sel=time=2021-06-08T18:49:21.024000000Z&sel_method=nearest
sel=time=1623178161024000000&sel_method=nearest
sel=time=nearest::2021-06-08T184921.024000000Z
```

Impact:

* time slicing through `sel=time` is unreliable;
* clients often need to fallback to `bidx=<n>` when using the unpatched `main` image.

## What this patch changes

Patch files:

* `docker/titiler-eopf-patched/Dockerfile`
* `docker/titiler-eopf-patched/patch_titiler_eopf.py`

Behavior changes:

* Relaxes `SelDimStr` validation to accept `:` in `sel` values (ISO datetime).
* Updates `titiler.eopf.reader.GeoZarrReader._get_variable` selection logic to:
  * support `sel_method` cleanly,
  * support inline `method::value` in `sel`,
  * cast datetime selectors to `datetime64[ns]` for compatibility with pandas/xarray.

## Build patched image

From repository root:

```bash
task titiler:eopf:build:patched
```

Image name:

* `titiler-eopf:patched`

## Run patched image against CWL results

From repository root:

```bash
task titiler:eopf:run:results:patched TITILER_PORT=8081
```

This resolves `DATA_ROOT` from `cwl-tests/results.json` (`zarr_stac_catalog.location`) and starts TiTiler with that mount.

## Time request format

Preferred request format:

* `sel=time=<ISO-8601 datetime>`
* `sel_method=nearest`

Example:

```bash
curl -o ndwi-time.png \
"http://127.0.0.1:8081/collections/water-bodies/items/water-bodies/preview.png?variables=/measurements:ndwi&sel=time=2021-06-08T18:49:21.024000000Z&sel_method=nearest&rescale=-1,1&colormap_name=viridis"
```

Notes:

* `bidx=<n>` remains a valid fallback for explicit time-index selection.
* Patch scope is local to this repository and image; upstream image behavior may differ by tag.

## Upstream tracking

This behavior is tracked in an upstream issue draft:

* [`UPSTREAM_ISSUE_titiler-eopf_sel-time.md`](../../UPSTREAM_ISSUE_titiler-eopf_sel-time.md)

The issue captures:

* failing `sel=time` requests on `ghcr.io/eopf-explorer/titiler-eopf:main`,
* reproducible 422/500 error patterns,
* proposed fixes for selector validation and datetime casting.
