"""Compatibility module re-exporting CLI and core helpers."""

from stac_collection.cli import to_stac
from stac_collection.contract import get_spatial_extent, get_temporal_extent, validate_parallel_inputs
from stac_collection.writer import run_to_stac


if __name__ == "__main__":
    to_stac()
