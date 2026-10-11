# Changelog

## [2.0.0]

- CWL v1.2 producer and typed application inputs with standalone schema definitions.
- GeoZarr convention validation and TiTiler-EOPF 0.12.2 compatible multiscales output.
- S3 producer wrapping with eoap-cwlwrap and mastering 2.0.0 stage-out, including complete Zarr v2/v3 stores.
- Kubernetes viewer, GeoParquet STAC index publication, real Sentinel-2 processing and time selection.
- Updated notebook documentation and locally rendered workflow diagrams.
- Candidate CI validates processing and conventions, scans containers, and publishes digest-pinned CWL/OCI artifacts.
