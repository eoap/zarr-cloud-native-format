# How-To: Compatible TiTiler-EOPF image

The Dockerfile pins the upstream filesystem-reader commit
`b0beec2a9c44ff030e2eef5cfc4622bd9ac19565` by GHCR digest. Current upstream
`main` requires a STAC API; it does not use the `TITILER_EOPF_STORE_URL`
filesystem configuration used by these labs.

The guarded patch handles GeoZarr convention v0.1 layout assets that point to
DataArrays, filters overview selection by variable, and casts datetime selectors
to nanosecond precision. The pinned dependency already accepts ISO colons and
inline selection methods; the build checks that support and fails if the
expected upstream reader blocks change.

```sh
task titiler:eopf:build:patched
task titiler:eopf:run:results:patched TITILER_PORT=8081
```

The local run mounts the catalog named by `zarr_stac_catalog` in
`cwl-tests/results.json`. All local TiTiler run tasks default to
`titiler-eopf:patched`; build the image first.

Use an advertised variable from `/dataset/keys`, which may be `/:ndwi` when
the GeoZarr multiscale layout is at the root. The HTML client maps the STAC
measurement expression to the unique matching advertised variable.

The supported nearest time selector is `sel=time=nearest::<ISO datetime>`:

```sh
curl -o ndwi-time.png \
  'http://127.0.0.1:8081/collections/water-bodies/items/water-bodies/preview.png?variables=/:ndwi&sel=time=nearest::2021-06-08T18:49:21.024000000Z&rescale=-1,1&colormap_name=viridis'
```

`bidx=<n>` remains available for explicit time-index selection. Do not substitute
`sel_method=nearest`: the pinned reader uses the inline selector DSL.

For separate Kubernetes server/client deployments and reproducible validation,
see [Display producer outputs on Kubernetes](titiler-eopf-kubernetes.md).
The [historical issue draft](https://github.com/eoap/zarr-cloud-native-format/blob/main/UPSTREAM_ISSUE_titiler-eopf_sel-time.md)
describes earlier moving-image failures rather than the currently pinned API.
