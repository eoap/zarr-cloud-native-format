# How-To: TiTiler-EOPF with STAC Collection Output

Use this mode when `stac-zarr` emits STAC Collection output (`--stac-object-type collection`, default).

## 1) Generate Zarr + STAC Collection

```bash
cd command-line-tools/stac-zarr
uv run --with-editable . stac-zarr \
  --stac-catalog /data/work/github/eoap/zarr-cloud-native-format/stac-collection-artifact \
  --stac-object-type collection \
  --overview-levels 2 \
  --consolidate \
  --titiler-eopf-compatible
```

## 2) Run TiTiler-EOPF

From repository root:

```bash
docker run --rm -it \
  -p 8080:80 \
  -e TITILER_EOPF_STORE_URL=file:///data/ \
  -v "$(pwd)/command-line-tools/stac-zarr":/data \
  ghcr.io/eopf-explorer/titiler-eopf:latest
```

## 3) Check available variables

```bash
curl "http://127.0.0.1:8080/collections/water-bodies/items/water-bodies/dataset/keys"
```

Typical base variables:

* `/measurements:ndwi`
* `/measurements:water-bodies`

## 4) Render preview

NDWI first time slice:

```bash
curl -o ndwi.png \
"http://127.0.0.1:8080/collections/water-bodies/items/water-bodies/preview.png?variables=/measurements:ndwi&bidx=1&rescale=-1,1&colormap_name=viridis"
```

Water-bodies mask:

```bash
curl -o water.png \
"http://127.0.0.1:8080/collections/water-bodies/items/water-bodies/preview.png?variables=/measurements:water-bodies&bidx=1&rescale=0,1&colormap_name=viridis"
```

## 5) Time-based request (recommended)

Use ISO timestamp with `sel=time`:

```bash
curl -o ndwi-time.png \
"http://127.0.0.1:8080/collections/water-bodies/items/water-bodies/preview.png?variables=/measurements:ndwi&sel=time=2021-06-28T19:03:24Z&sel_method=nearest&rescale=-1,1&colormap_name=viridis"
```

Tip:

* `sel=time` expects ISO datetime strings
* `bidx=1` is a fallback for selecting first time slice
* For interactive map usage, see `How-To: TiTiler-EOPF HTML Client`
