
## GeoZarr validation

Outputs use the published Pilot `v0.1` proj, spatial, and multiscales conventions.
Each measurement and overview array carries its own projection and spatial
metadata. Conversion validates the completed store using `geozarr-toolkit` and
checks declarations, array dimensions/shapes, and pyramid references.

From the repository root, validate an existing store with:

```bash
task compliance:check:store STORE=/absolute/path/to/output.zarr
```

Run generated-store validation and rejection tests with
`task compliance:check:geozarr-toolkit`, or all checks with
`task compliance:check:all`.

The installed module exposes validation through the Python API:

```python
from stac_zarr import validate_geozarr_store

validate_geozarr_store("output.zarr")  # Raises ValueError on invalid metadata.
```

You can also pass an open `zarr.Group` or a `pathlib.Path`. Path-based validation
opens the store read-only and reads live metadata. The implementation calls
`geozarr_toolkit.validate_attrs` for each node and checks store references.
Conversion invokes this same API before writing STAC output.

The installed validation command is:

```bash
stac-zarr-validate output.zarr
```

It exits with status 1 on failure and status 0 on success.

TiTiler-EOPF 0.12.2 integration uses complete-store STAC asset URLs and group-based `multiscales.layout` entries. Use item-mode output for STAC API publication; see the Kubernetes publication guide.
