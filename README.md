# STAC Datacube extension and Zarr Cloud-Native format

This repository provides a cloud-native Earth-Observation Application Package that shows how to produce a Zarr multi-dimensional dataset (x, y, t) and describe it as a STAC Collection using the [STAC Datacube Extension](https://stac-extensions.github.io/datacube/).

This repository shows how to process EO data into datacubes and publish them in a way that follows cloud-native and STAC standards.

## Application

The Earth-Observation Application Package detects water bodies using the NDWI index and the Otsu automatic threshold on a stack of Sentinel-2 Level-2A products.

## Features

- **Zarr Output**: Outputs a datacube of detected water bodies over an area of interest (datacube spatial dimensions x and y) and over a time of interest (datacube temporal dimension) as a Zarr dataset.
- **STAC Metadata**: The Zarr dataset is an asset described by a STAC Collection including the [STAC Datacube Extension](https://stac-extensions.github.io/datacube/) to include the metadata about the datacube dimensions and variables.

## Workflow Overview

The workflow is based on one of the workflows of the https://github.com/eoap#mastering-earth-observation-application-packaging-with-cwl module extended to provide the temporal element.

The steps are:

1. **STAC API Discovery**: defines a STAC API search request and queries a STAC API endpoint returning a FeatureCollection
2. **SearchResults**: extracts the discovered STAC Items `self` href.
3. **Water bodies detection**: a sub-workflow that runs: 
  * **Cropping**: Crops Sentinel-2 imagery to the Area of Interest (AOI).
  * **Normalized Difference Water Index (NDWI)**: Computes NDWI to identify water bodies.
  * **Otsu Thresholding**: Applies Otsu's thresholding method to binarize NDWI values.
4. **Zarr dataset creation and STAC Metadata**: Converts the results into a Zarr dataset and generates the STAC Collection including [STAC Datacube Extension](https://stac-extensions.github.io/datacube/).

## Running the Workflow

Use the approach described in https://github.com/eoap/dev-platform-eoap to run this module on Minikube using skaffold

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
