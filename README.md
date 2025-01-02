# Zarr Cloud-Native Workflow for Water Body Detection

This repository provides a cloud-native Earth-Observation Application Package for detecting water bodies over time using Sentinel-2 data. 

The workflow leverages Common Workflow Language (CWL) and outputs data in the Zarr format, described using the [STAC Datacube Extension](https://stac-extensions.github.io/datacube/).

## Features

- **Zarr Output**: Outputs water body data as Zarr files for cloud-native geospatial processing.
- **STAC Metadata**: Includes STAC metadata for integration with EO datalakes.
- **Scalable processing**: Designed to process multiple Sentinel-2 STAC items in parallel.

## Workflow Overview

The workflow is based on one of the workflows of the https://github.com/eoap#mastering-earth-observation-application-packaging-with-cwl module and includes the following steps:

1. **Cropping**: Crops Sentinel-2 imagery to the Area of Interest (AOI).
2. **Normalized Difference Water Index (NDWI)**: Computes NDWI to identify water bodies.
3. **Otsu Thresholding**: Applies Otsu's thresholding method to binarize NDWI values.
4. **STAC Metadata Creation**: Generates STAC items for the detected water bodies.
5. **Zarr Conversion**: Converts the results into a Zarr dataset with Datacube metadata.

## Running the Workflow

Use the approach described in https://github.com/eoap/dev-platform-eoap to run this module on Minikube using skaffold

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
