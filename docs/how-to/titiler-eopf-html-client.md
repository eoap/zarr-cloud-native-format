# How-To: Start TiTiler-EOPF and the HTML Client

This page shows how to run TiTiler-EOPF and open the local HTML viewer:

* Viewer file: `examples/titiler-eopf-client.html`
* TiTiler API default: `http://127.0.0.1:8080`

## 1) Start TiTiler-EOPF

From repository root:

```bash
task titiler:eopf:run DATA_ROOT=command-line-tools/stac-zarr TITILER_PORT=8080
```

This serves Zarr/STAC content mounted from `command-line-tools/stac-zarr`.

If you need patched time-selection behavior for `ghcr.io/eopf-explorer/titiler-eopf:main`:

```bash
task titiler:eopf:build:patched
task titiler:eopf:run:results:patched TITILER_PORT=8081
```

## 2) Serve the HTML client on another port

From repository root, in a second terminal:

```bash
python -m http.server 8090
```

Open:

```text
http://127.0.0.1:8090/examples/titiler-eopf-client.html
```

## 3) Fill the client fields

Use:

* `Base URL`: `http://127.0.0.1:8080` (or `http://127.0.0.1:8081` for patched run)
* `Collection ID`: `water-bodies`
* `Item ID`: `water-bodies`

Then click:

1. `Load measurements and dates`
2. Select measurement/date
3. `Render layer`

## 4) Notes

* Keep TiTiler and the static server on different ports.
* If date values are not returned by TiTiler collection endpoint, the client can read fallback `collection.json`.
* For NDWI, a common display range is `rescale=-1,1`.
* For patch details and exact time query format, see `How-To: TiTiler-EOPF Local Patch for Time Selection`.
* Upstream tracking for `sel=time` failures is documented in `UPSTREAM_ISSUE_titiler-eopf_sel-time.md`.
