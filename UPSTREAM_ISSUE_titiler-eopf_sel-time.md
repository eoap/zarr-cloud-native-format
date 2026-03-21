# Bug: `sel=time` handling is broken for ISO datetimes on `titiler-eopf:main`

## Summary

Time selection for GeoZarr endpoints is currently inconsistent/broken on `ghcr.io/eopf-explorer/titiler-eopf:main`:

1. API validation rejects common ISO datetime values in `sel` (422).
2. Alternative accepted forms can fail later in xarray/pandas with datetime dtype errors (500), e.g. `datetime64[Y] is not supported`.

This prevents robust time-based visualization requests and forces fallback to `bidx`.

## Environment

* Image: `ghcr.io/eopf-explorer/titiler-eopf:main`
* Endpoints used:
  * `/collections/{collection_id}/items/{item_id}/preview.png`
  * `/collections/{collection_id}/items/{item_id}/.../tilejson.json`
* Dataset: any GeoZarr dataset exposing a `time` dimension (collection/item IDs below are examples).

## Reproduction

### 1) Start container

```bash
docker run --rm -it \
  -p 8080:80 \
  -e TITILER_EOPF_STORE_URL=file:///data/ \
  -v "<DATA_ROOT>":/data \
  ghcr.io/eopf-explorer/titiler-eopf:main
```

### 2) Request with standard ISO datetime in `sel`

Use a collection/item that exists in your local store (replace placeholders):

```bash
curl -i \
"http://127.0.0.1:8080/collections/<collection_id>/items/<item_id>/preview.png?variables=<group:variable>&sel=time=2021-06-08T18:49:21.024000000Z&sel_method=nearest"
```

Concrete example used in this report:

```bash
curl -i \
"http://127.0.0.1:8080/collections/water-bodies/items/water-bodies/preview.png?variables=/measurements:ndwi&sel=time=2021-06-08T18:49:21.024000000Z&sel_method=nearest&rescale=-1,1&colormap_name=viridis"
```

### 3) Observed response

`422 Unprocessable Entity`:

* `"String should match pattern '^[^=]+=((nearest|pad|ffill|backfill|bfill)::)?[^=::]+$'"`
* input rejected because value contains `:`.

### 4) Alternative requests

These are accepted by validation but fail in reader/indexing:

* `sel=time=1623178161024000000&sel_method=nearest`
* `sel=time=nearest::2021-06-08T184921.024000000Z`

Observed failure:

* `500 Internal Server Error`
* `TypeError: dtype=datetime64[Y] is not supported. Supported resolutions are 's', 'ms', 'us', and 'ns'`

## Expected behavior

Time selection should work with standard ISO datetimes:

* `sel=time=<ISO-8601>&sel_method=nearest`

Example:

```text
sel=time=2021-06-08T18:49:21.024000000Z&sel_method=nearest
```

## Actual behavior

Current validator pattern for `SelDimStr` disallows `:` in `sel` value, which conflicts with valid ISO datetime formats.

Additionally, reader-side casting can produce unsupported datetime unit paths when numeric selectors are used.

## Likely root causes

1. `titiler.xarray.dependencies.SelDimStr` regex is too restrictive for datetime use:
   * current: `^[^=]+=((nearest|pad|ffill|backfill|bfill)::)?[^=::]+$`
2. In `titiler.eopf.reader.GeoZarrReader._get_variable`, datetime selector casting path may coerce to problematic units instead of normalizing to `datetime64[ns]`.
3. Method handling is split between:
   * inline `sel=time=nearest::<value>`
   * `sel_method=nearest`
   and behavior is not consistent across validation and reader parsing.

## Proposed fix

1. Relax `SelDimStr` to allow `:` in value part for ISO datetimes.
2. In EOPF reader selector casting:
   * detect datetime dimensions,
   * normalize selected values to `datetime64[ns]`,
   * support both inline `method::value` and `sel_method`.
3. Add tests for:
   * ISO datetime `sel` + `sel_method`
   * nearest selection against time dimension
   * regression for current 422 and 500 scenarios.

## Temporary local workaround

Using `bidx=<n>` works, but does not provide semantic time selection and is not ideal for client UX.
