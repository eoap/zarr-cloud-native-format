# Bug: `sel=time` is unreliable on `ghcr.io/eopf-explorer/titiler-eopf:main`

## Summary

On `ghcr.io/eopf-explorer/titiler-eopf:main`, time selection with `sel=time=...` is not reliable for GeoZarr datasets with a temporal dimension:

1. Standard ISO datetime selectors can be rejected at request validation (`422`).
2. Other accepted selector forms can fail later during xarray/pandas selection (`500`).

This blocks deterministic time-based rendering and forces index-based fallback (`bidx`), which is not equivalent.

## Environment

- Image: `ghcr.io/eopf-explorer/titiler-eopf:main`
- Endpoint class: GeoZarr collection/item endpoints (`preview.png`, `tilejson.json`, tiles)
- Dataset requirement: any dataset with `time` coordinate/dimension

## Reproduction

### 1) Start TiTiler-EOPF

```bash
docker run --rm -it \
  -p 8080:80 \
  -e TITILER_EOPF_STORE_URL=file:///data/ \
  -v "<DATA_ROOT>":/data \
  ghcr.io/eopf-explorer/titiler-eopf:main
```

### 2) Request using ISO datetime + `sel_method=nearest`

```bash
curl -i \
"http://127.0.0.1:8080/collections/<collection_id>/items/<item_id>/preview.png?variables=<group:variable>&sel=time=2021-06-08T18:49:21.024000000Z&sel_method=nearest"
```

## Observed behavior

### A) Validation error (`422`)

The request above can fail with:

- `String should match pattern '^[^=]+=((nearest|pad|ffill|backfill|bfill)::)?[^=::]+$'`

This regex disallows `:` in the selector value, but ISO datetimes require `:`.

### B) Runtime selection error (`500`)

Alternative selector shapes can pass validation but fail later in selection:

- `sel=time=1623178161024000000&sel_method=nearest`
- `sel=time=nearest::2021-06-08T184921.024000000Z`

Observed traceback contains:

- `TypeError: dtype=datetime64[Y] is not supported. Supported resolutions are 's', 'ms', 'us', and 'ns'`

## Expected behavior

Requests like below should work consistently:

```text
sel=time=<ISO-8601>&sel_method=nearest
```

Example:

```text
sel=time=2021-06-08T18:49:21.024000000Z&sel_method=nearest
```

## Likely root causes

1. `SelDimStr` validation is too restrictive for ISO datetime values.
2. Reader-side datetime casting/normalization in temporal `.sel(...)` path is not robust.
3. Handling of inline `method::value` vs `sel_method` is inconsistent.

## Proposed upstream fix

1. Relax selector validation so ISO datetime values are accepted.
2. In temporal selection path, normalize selectors to a pandas/xarray-safe datetime precision (e.g. `datetime64[ns]`).
3. Harmonize behavior across:
   - `sel=time=<value>&sel_method=<method>`
   - `sel=time=<method>::<value>`
4. Add regression tests for:
   - ISO datetime selector acceptance
   - nearest temporal selection
   - previously failing `422` and `500` cases

## Local status / workaround

- `bidx=<n>` works but is index-based and not semantically equivalent to datetime selection.
- A local patched image in this repo fixes `sel=time` behavior for our use case:
  - `docker/titiler-eopf-patched/Dockerfile`
  - `docker/titiler-eopf-patched/patch_titiler_eopf.py`
  - `docs/how-to/titiler-eopf-patch.md`
