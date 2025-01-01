# Zarr Cloud-Native Workflow for Water Body Detection

## Overview

This module implements a cloud-native approach to detecting water bodies using Sentinel-2 data. The workflow uses the Common Workflow Language (CWL) for defining tasks and outputs data in the Zarr format, fully compatible with the STAC Datacube Extension.

By integrating Sentinel-2 data with Zarr and CWL, the workflow enables:

* Efficient parallel processing of geospatial data.
* Scalable cloud-native solutions for environmental monitoring.
* Interoperable metadata for easy integration with Earth Observation (EO) datalakes.

## Workflow Steps

1. Crop Sentinel-2 Imagery

Crop Sentinel-2 imagery to the defined Area of Interest (AOI) using the input bounding box and Sentinel-2 bands.

Input:
* STAC item URL
* Bounding box (e.g., -121.399,39.834,-120.74,40.472)
* EPSG code (e.g., EPSG:4326)

Output: 
* Cropped GeoTIFF images

2. Compute NDWI

Apply the Normalized Difference Water Index (NDWI) formula to the cropped imagery:

Input: 
* Cropped Sentinel-2 bands (green and nir)

Output: 
* NDWI GeoTIFF

3. Apply Otsu's Thresholding

Use Otsu's thresholding algorithm to convert the NDWI to a binary water mask.

Input: 
* NDWI GeoTIFF

Output: 
* Binary water mask GeoTIFF

4. Convert to Zarr Datacube

Aggregate binary water masks over time into a Zarr datacube. The resulting dataset includes temporal and spatial dimensions.

Input: 
* Binary water masks

Output: 
* Zarr dataset

5. Generate STAC Metadata

Produce STAC items for each step, describing the results with the appropriate metadata.

Input: 
* Process outputs

Output: 
* Zarr encoded result
* STAC item (including Datacube metadata)