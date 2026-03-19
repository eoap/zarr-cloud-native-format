# stac-eopf-product

Convert a STAC Catalog into an EOPF Zarr product and emit a STAC Catalog pointing to that store.

## CLI

```bash
stac-eopf-product \
  --stac-catalog /path/to/stac-catalog \
  --resolution 20 \
  --chunks manual \
  --chunk-x 512 \
  --chunk-y 512 \
  --chunk-time 1
```

Options:
- `--stac-catalog` (required): directory containing `catalog.json`
- `--resolution` (optional): target output resolution used by `odc.stac.stac_load`
- `--chunks` (`manual|auto`): chunking mode
- `--chunk-x`, `--chunk-y`, `--chunk-time`: manual chunk sizes

## Input Contract

The input STAC Collection must define `item_assets`.  
Those keys are treated as the measurement contract and every Item must include each declared asset key.

If `item_assets` is missing or items do not contain all declared measurements, conversion fails with a validation error.
