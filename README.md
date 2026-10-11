# STAC Datacube extension and Zarr Cloud-Native format

This repository goal is to provide CWL workflows, examples, and documentation for producing and consuming Earth Observation data in cloud-native Zarr format with STAC metadata.

This repository provides a cloud-native Earth-Observation Application Package that shows how to produce a Zarr multi-dimensional dataset (x, y, t) and describe it as a STAC Collection using the [STAC Datacube Extension](https://stac-extensions.github.io/datacube/).

This repository shows how to process EO data into datacubes and publish them in a way that follows cloud-native and STAC standards.

## Application

The Earth-Observation Application Package detects water bodies using the NDWI index and the Otsu automatic threshold on a stack of Sentinel-2 Level-2A products.

## Features

- **Zarr Output**: Outputs a datacube of detected water bodies over an area of interest (datacube spatial dimensions x and y) and over a time of interest (datacube temporal dimension) as a Zarr dataset.
- **STAC Metadata**: The Zarr dataset is an asset described by a STAC Collection including the [STAC Datacube Extension](https://stac-extensions.github.io/datacube/) to include the metadata about the datacube dimensions and variables.

## Documentation

See the full guide and runnable walkthrough here: https://eoap.github.io/zarr-cloud-native-format/exploitation/

Covers:

* Producing a Zarr store with an Application Package.
* Consuming a Zarr store with an Application Package
* Inspecting the generated STAC catalog.
* Opening datasets with xarray to inspect the Zarr store metadata and data.
* Notes on metadata, consolidated stores, and troubleshooting.


## Application Package Overview

### Producer Application Package

The workflow is based on one of the workflows of the https://github.com/eoap#mastering-earth-observation-application-packaging-with-cwl module extended to provide the temporal element.

The steps are:

1. **STAC API Discovery**: defines a STAC API search request and queries a STAC API endpoint returning a FeatureCollection
2. **SearchResults**: extracts the discovered STAC Items `self` href.
3. **Water bodies detection**: a sub-workflow that runs: 
  * **Cropping**: Crops Sentinel-2 imagery to the Area of Interest (AOI).
  * **Normalized Difference Water Index (NDWI)**: Computes NDWI to identify water bodies.
  * **Otsu Thresholding**: Applies Otsu's thresholding method to binarize NDWI values.
4. **Zarr dataset creation and STAC Metadata**: Converts the results into a Zarr dataset and generates the STAC Collection including [STAC Datacube Extension](https://stac-extensions.github.io/datacube/).

### Consumer Application Package

The workflow reads the produced STAC Catalog describing the detected water bodies Zarr store and produces the mean over the time dimension.

There's a single step that:

1. **Reads STAC Catalog**: read the STAC Catalog and inspect the STAC Collection
2. **Reads the Zarr store**: read the Zarr store STAC Asset
3. **Calculates the mean**: use `xarray` to calculate the mean over the time dimension
4. **Exports to GeoTIFF**: user `rioxarray` to write a GeoTIFF
5. **Generates STAC Catalog**: create a STAC Catalog describing the result

## Running the Application Packages and notebooks

Use the approach described in https://github.com/eoap/dev-platform-eoap to run this module on Minikube using skaffold

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

## Kubernetes viewer

See [Display producer outputs on Kubernetes](docs/how-to/titiler-eopf-kubernetes.md) for the separate TiTiler server and HTML client deployments and publication of completed module outputs.

## Packaging and processing-image validation

Python packages use Hatchling and Python 3.12. Each package keeps its runtime and
development dependency hashes under `requirements/`. Run `hatch run dev:check` and
`hatch run test:test` from the repository root or a `command-line-tools/` package.
The bootstrap command explicitly installs the lock because Hatch skips install
hooks when `skip-install = true`.

Processing Dockerfiles build a wheel with Hatch in Rocky Linux 10.1 and install
it into `/app/venv` in a separate Rocky runtime. Processing runs as `neo`
(UID/GID 2000); the runtime checks dependencies, checks its CLI, and removes its
virtual-environment pip. Build a tool with
`docker build -t crop:test command-line-tools/crop`.

Keep the EOPF and STAC-Zarr environments separate: the accepted EOPF dependency
set uses Zarr 2, while the GeoZarr writer uses Zarr 3. Publication tooling has its
own `requirements/cwl-release.txt` hash lock because its Click requirement differs
from EOPF's. The upstream Go `yq` utility and TiTiler service image are explicit
exceptions to the Python-wheel processing model; neither contains a module-owned
Python processing package.

The wrapper restores published EOAP schema imports after SDK serialization;
module-owned types stay inline in the standalone CWL. It never uses a packing
command. Passing local package gates and container smoke checks prepares a
candidate; real-data notebook acceptance on Kubernetes and validation of published
candidate artifacts are required before release promotion.
