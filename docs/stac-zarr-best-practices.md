# TL;DR — STAC Zarr Best Practices

* Use STAC Items for single scenes or time slices, and STAC Collections for datasets spanning multiple times/regions. Each Item or Collection may reference one Zarr store.
* One STAC asset = one Zarr group (not individual arrays). Arrays and subgroups live inside the asset’s Zarr hierarchy.
* Always link the Zarr store using `rel: store`, pointing to the root of the (native or virtual) Zarr store. All Zarr assets are assumed to live under this store.
* Use the correct Zarr media type with version:
  * `application/vnd.zarr; version=2`
  * `application/vnd.zarr; version=3`
* Optionally add `profile=multiscales` (convention hint, not yet standard).
* Do not expose arrays as assets.
* Expose bands via the bands array:
  * One variable = one band → name = variable name
  * One variable, many bands → encode band selection in name
  * Multiscales → bands are resolution-agnostic; resolution is inferred from the Zarr layout
* Asset href always points to a Zarr group, never directly to an array.
* Clients access arrays by path-joining asset.href + band.name.
* For multiresolution data:
  * Either expose one asset per resolution, or
  * A single multiscales asset pointing to the parent group (preferred when resolutions are tightly coupled)
* Use STAC extensions consistently:
  * Datacube: describe variables and dimensions (cube:variables, cube:dimensions)
  * Projection: spatial reference (proj:*)
  * Raster: raster properties (resolution, nodata, dtype)
  * CF: climate/forecast semantics (cf:standard_name, units, etc.)
* Virtual Zarr stores (Kerchunk, VirtualiZarr, icechunk):
  * Treat them like native Zarr
  * `rel: store` points to the reference/entrypoint
  * Assets may carry role `"virtual"`
  * Source files may be referenced separately with role "source"
* Link Templates MAY be used to advertise variable-level access without enumerating arrays as assets.

In short: 

* STAC describes what is in the Zarr store, not how to traverse it.
* Zarr handles structure; STAC handles discovery, semantics, and access hints.