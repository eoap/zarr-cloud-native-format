# Display producer outputs on Kubernetes

The development-platform deployment provides separate TiTiler server and client
Deployments and ClusterIP Services. Follow the
[development-platform Zarr deployment guide](https://github.com/eoap/dev-platform-eoap/tree/feature/review-stall/zarr-cloud-native-format)
for Skaffold deployment, forwarding, publication and integration tests.

The existing HTML client accepts `window.EOAP_TITILER_CONFIG` from
`examples/titiler-eopf-config.js`. Kubernetes serves a runtime configuration with
`apiBaseUrl: "/api"`, `dataBaseUrl: "/data/"` and default collection/item IDs
`water-bodies`. Outside Kubernetes the empty configuration retains the local
Docker settings in the form.

After the producer completes, run:

```sh
task titiler:eopf:publish RESULTS=cwl-tests/results.json
```

The publication helper reads `zarr_stac_catalog.location` or `.path`, checks the
local Zarr v3 stores and atomically updates `titiler-data`. This requires local
filesystem outputs; paths must also be visible to the viewer pods. Kubernetes
mounts `/workspace` and `/calrissian` read-only into both viewers. Restart TiTiler
after changing publication to clear its open-dataset cache; the development-platform
`viewer:publish` task does this automatically.

The derived image is pinned to upstream's last compatible filesystem-reader
commit, with guarded fixes for GeoZarr DataArray layout entries and datetime
selection. Build it with `task titiler:eopf:build:patched`; local run tasks now
default to `titiler-eopf:patched`. Current upstream `main` requires a STAC API and
is not a drop-in filesystem-server replacement.
