from datetime import (
    datetime,
    timezone
)
from eopf.product import EOProduct, EOGroup, EOVariable
from eopf.store.zarr import EOZarrStore

from pathlib import Path
from pystac import (
    Asset,
    Catalog,
    Item,
    MediaType,
    STACObject,
    read_file as read_stac_file,
    write_file as write_stac_file
)
from typing import (
    Any,
    List
)
from xarray import Dataset

import eopf.common.constants as c
import numpy as np
import click, os, pystac, zarr
from loguru import logger
from odc.stac import stac_load

def extract_crs(item):
    """Extract CRS from a STAC item."""
    epsg = item.properties.get("proj:epsg")
    if epsg:
        return f"epsg:{epsg}"
    code = item.properties.get("proj:code")
    if code and code.upper().startswith("EPSG:"):
        return code.lower()  # "epsg:32633"
    raise ValueError("CRS not found in item properties")


def _to_datetime(npdatetime):
    ns = npdatetime.astype("datetime64[ns]").astype("int64")

    # datetime has microsecond resolution, so split seconds / microseconds
    seconds = ns // 1_000_000_000
    micros = (ns % 1_000_000_000) // 1_000

    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(microsecond=int(micros))


@click.command()
@click.option(
    "--stac-catalog",
    type=click.Path(
        path_type=Path,
        exists=True,
        readable=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True
    ),
    help="STAC Catalog file",
    required=True,
)
@click.option(
    "--output-dir",
    type=click.Path(
        path_type=Path,
        exists=False,
        readable=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    ),
    default=Path('.'),
    required=True,
    help="Output directory path",
)
def to_eopf(
    stac_catalog: Path,
    output_dir: Path
):
    logger.info(f"Reading STAC catalog from {stac_catalog}...")
    catalog: STACObject = read_stac_file(stac_catalog)

    if not isinstance(catalog, Catalog):
        raise Exception(f"{stac_catalog} is not a valid STAC Catalog instance, found {type(catalog)}")

    items: List[Item] = list(catalog.get_all_items())

    logger.info(f"Found {len(items)} STAC Items in {stac_catalog} STAC Catalog")
    crs = extract_crs(items[0])

    # Load data as a single xarray dataset (same as before)
    stac_catalog_dataset: Dataset = stac_load(
        items,
        bands=["data"],
        crs=crs,
        resolution=10,
        chunks={"x": 512, "y": 512, "time": 1},
        groupby="time",
    )

    logger.info("Loaded data using odc.stac")

    product: EOProduct = EOProduct(name="water_bodies_eopf")
    product["measurements"] = EOGroup()

    # Convert xarray array → EOVariable (Dask-aware)
    da = stac_catalog_dataset["data"]                      # (time, y, x)
    product["measurements/water"] = EOVariable(
        data=da.data,                    # dask array
        dims=("time", "y", "x"),
        attrs={"description": "Detected water bodies"}
    )

    spatial_bbox = [
        float(min(stac_catalog_dataset.x.values)),
        float(min(stac_catalog_dataset.y.values)),
        float(max(stac_catalog_dataset.x.values)),
        float(max(stac_catalog_dataset.y.values))
    ]

    start_datetime = _to_datetime(stac_catalog_dataset.time.values.min())
    end_datetime = _to_datetime(stac_catalog_dataset.time.values.max())

    item: Item = Item(
        id="water-bodies",
        geometry=items[0].geometry,
        bbox=spatial_bbox,
        datetime=start_datetime,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        properties={}
    )

    product.attrs["stac_discovery"] = item.to_dict(include_self_link=False)

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing EOPF Zarr product to {output_dir}")

    with EOZarrStore(
        url=output_dir.absolute().as_uri()
    ).open(
        mode=c.OpeningMode.CREATE_OVERWRITE
    ) as store:
        store["water_bodies_eopf"] = product

    logger.info("Done writing EOPF product! Serializing the STAC Item...")

    item.add_asset(
        key="store",
        asset=Asset(
            href="water_bodies_eopf.zarr",
            media_type=f"{MediaType.ZARR}; version=3",
            roles=["data", "zarr"],
            title="Zarr Store",
            description="Detected water bodies in Zarr cloud-native format"
        )
    )

    item.add_asset(
        key="data-variable",
        asset=Asset(
            href="water_bodies_eopf.zarr/measurements/{measurement}",
            media_type=f"{MediaType.ZARR}; version=3",
            roles=["data", "zarr"],
            title="Detected water bodies",
            description="Detected water bodies in Zarr cloud-native format",
            extra_fields={
                "variables": {
                    "measurement": {
                        "type": "string",
                        "enum": [str(group) for group in product["measurements"]]
                    }
                }
            },
        )
    )

    output_item: Path = Path(output_dir, 'item.json')
    write_stac_file(
        obj=item,
        include_self_link=True,
        dest_href=output_item
    )

if __name__ == "__main__":
    to_eopf()