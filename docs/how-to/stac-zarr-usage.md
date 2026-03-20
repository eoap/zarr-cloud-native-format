# How-To: Use `stac-zarr`

This page documents practical `stac-zarr` usage patterns.

## What `stac-zarr` does

`stac-zarr` reads an input STAC Catalog and writes:

* a Zarr v3 store (`<collection-id>.zarr`)
* output STAC metadata as either:
  - a STAC Collection (default)
  - a STAC Item (`--stac-object-type item`)

## Input requirements

The input STAC Collection must define `item_assets`.

`item_assets` is used as the measurement contract:

* each key becomes a measurement
* each input Item must include all declared measurement keys

## Basic command

```bash
cd command-line-tools/stac-zarr
uv run --with-editable . stac-zarr \
  --stac-catalog /path/to/stac-catalog-dir
```

## Output STAC object type

Collection output (default):

```bash
stac-zarr --stac-catalog /path/to/stac-catalog-dir --stac-object-type collection
```

Item output:

```bash
stac-zarr --stac-catalog /path/to/stac-catalog-dir --stac-object-type item
```

## Overviews / pyramids

```bash
stac-zarr --stac-catalog /path/to/stac-catalog-dir --overview-levels 2
```

Reducer controls:

* `--continuous-overview-reducer mean|max|median|nearest`
* `--categorical-overview-reducer mean|max|median|nearest`

## Resolution and chunking

```bash
stac-zarr --stac-catalog /path/to/stac-catalog-dir \
  --resolution 10 \
  --chunks manual \
  --chunk-x 512 \
  --chunk-y 512 \
  --chunk-time 1
```

Use auto chunking:

```bash
stac-zarr --stac-catalog /path/to/stac-catalog-dir --chunks auto
```

## TiTiler-EOPF compatibility mode

For current TiTiler-EOPF behavior, use:

```bash
stac-zarr --stac-catalog /path/to/stac-catalog-dir \
  --titiler-eopf-compatible
```

This suppresses root multiscales attrs that TiTiler-EOPF currently interprets as root scale groups.

## Consolidated metadata

Consolidation is on by default:

```bash
stac-zarr --stac-catalog /path/to/stac-catalog-dir --consolidate
```

Disable if needed:

```bash
stac-zarr --stac-catalog /path/to/stac-catalog-dir --no-consolidate
```
