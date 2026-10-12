"""Compatibility module re-exporting CLI and core helpers."""

from stac_collection.cli import to_stac
from stac_collection.contract import get_spatial_extent as get_spatial_extent
from stac_collection.contract import get_temporal_extent as get_temporal_extent
from stac_collection.contract import validate_parallel_inputs as validate_parallel_inputs
from stac_collection.writer import run_to_stac as run_to_stac

if __name__ == "__main__":
    to_stac()
