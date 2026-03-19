# Producer Outputs Contract

This page documents the expected outputs of `cwl-workflow/app-water-bodies.cwl#water-bodies`.

## Workflow outputs

The producer workflow emits three top-level directories:

* `zarr_stac_catalog`
* `stac_catalog`
* `eopf_product_stac_catalog`

## `stac_catalog`

Produced by the `stac-collection` step.

Expected content:

* `catalog.json` at the directory root
* one Collection child with `item_assets` declared
* Items containing COG assets from NDWI and Otsu stages

This output is the upstream input for both:

* `stac-zarr`
* `stac-eopf-product`

## `zarr_stac_catalog`

Produced by the `stac-zarr` step.

Expected content:

* a STAC catalog rooted at `catalog.json`
* a Collection with `rel=store` link to `<collection-id>.zarr`
* a Collection with Zarr media type for assets with multiscale profile
* a Collection with Datacube, Projection, and Raster extension metadata
* native Zarr v3 store written under `<collection-id>.zarr`

`stac-zarr` is collection-driven:

* measurement keys come from `collection.item_assets`
* each item must contain all declared measurement keys

## `eopf_product_stac_catalog`

Produced by the `stac-eopf-product` step.

Expected content:

* a STAC catalog rooted at `catalog.json`
* a Collection with `rel=store` link to `<collection-id>.zarr`
* a Collection with `application/vnd.zarr; version=2` media type references
* EOPF Zarr store written under `<collection-id>.zarr`

`stac-eopf-product` follows the same input contract:

* `collection.item_assets` is required
* measurements are derived from `collection.item_assets`
* items missing declared measurements fail validation

## Quick validation

Run:

```bash
task cwl:run:producer
```

Then inspect:

* output root `catalog.json` files
* Collection `links` for `rel=store`
* Collection assets and extension fields
