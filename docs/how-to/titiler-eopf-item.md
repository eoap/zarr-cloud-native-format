# How-To: TiTiler-EOPF with STAC Item Output

Use this mode when `stac-zarr` emits STAC Item output (`--stac-object-type item`).

## 1) Generate Zarr + STAC Item

```bash
cd command-line-tools/stac-zarr
uv run --with-editable . stac-zarr \
  --stac-catalog /data/work/github/eoap/zarr-cloud-native-format/stac-collection-artifact \
  --stac-object-type item \
  --overview-levels 2 \
  --consolidate \
  --titiler-eopf-compatible
```

Expected output example:

* `water-bodies/water-bodies.json` (Item)
* `water-bodies/water-bodies.zarr` (store)

## 2) Run TiTiler-EOPF

From repository root:

```bash
docker run --rm -it \
  -p 8080:80 \
  -e TITILER_EOPF_STORE_URL=file:///data/ \
  -v "$(pwd)/command-line-tools/stac-zarr":/data \
  ghcr.io/eopf-explorer/titiler-eopf:latest
```

## 3) Query item endpoints

```bash
curl "http://127.0.0.1:8080/collections/water-bodies/items/water-bodies/dataset/keys"
```

Preview:

```bash
curl -o ndwi-item.png \
"http://127.0.0.1:8080/collections/water-bodies/items/water-bodies/preview.png?variables=/measurements:ndwi&bidx=1&rescale=-1,1&colormap_name=viridis"
```

## 4) Optional mean aggregation

Use TiTiler algorithm endpoint parameter:

```bash
curl -o ndwi-mean-item.png \
"http://127.0.0.1:8080/collections/water-bodies/items/water-bodies/preview.png?variables=/measurements:ndwi&algorithm=mean&rescale=-1,1&colormap_name=viridis"
```

## 5) Notes on overviews

When `--overview-levels > 0`, `dataset/keys` can also list overview groups.

For user-facing UIs, prefer base measurement keys:

* `/measurements:ndwi`
* `/measurements:water-bodies`
* For interactive map usage, see `How-To: TiTiler-EOPF HTML Client`
