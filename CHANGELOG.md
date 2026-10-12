# Changelog

## [Unreleased]

- Hash-locked Hatch development and publication environments with required quality gates.
- Python 3.12 wheels and separate Rocky Linux 10.1 processing runtimes as UID/GID 2000.
- Preserve shared schema imports when serializing wrapped workflows.
- Regenerate GeoZarr models from published convention schemas with typed annotations.
- Emit valid scalar STAC raster resolution metadata and preserve public helper exports.

## [2.0.0]

- CWL v1.2 producer and typed application inputs with standalone schema definitions.
- GeoZarr convention validation and TiTiler-EOPF 0.12.2 compatible multiscales output.
- S3 producer wrapping with eoap-cwlwrap and mastering 2.0.0 stage-out, including complete Zarr v2/v3 stores.
- Kubernetes viewer, GeoParquet STAC index publication, real Sentinel-2 processing and time selection.
- Updated notebook documentation and locally rendered workflow diagrams.
- Candidate CI validates processing and conventions, scans containers, and publishes digest-pinned CWL/OCI artifacts.
