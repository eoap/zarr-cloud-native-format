"""Creates a STAC catalog with the detected water bodies""" ""

import os
import shutil
import click
from pystac import (
    Extent,
    SpatialExtent,
    TemporalExtent,
    Item,
    Catalog,
    Collection,
    CatalogType,
    read_file,
)
from pystac.media_type import MediaType
from pystac.item_assets import ItemAssetDefinition
import rio_stac
from loguru import logger
from pathlib import Path


def get_temporal_extent(items):
    """Get temporal extent from a list of STAC items."""
    times = [item.datetime for item in items]
    if not times:
        raise ValueError("No datetime found in item properties")
    return [min(times), max(times)]


def get_spatial_extent(items):
    """Get spatial extent from a list of STAC items."""
    bboxes = [item.bbox for item in items if item.bbox]
    if not bboxes:
        raise ValueError("No bbox found in item properties")
    min_x = min(bbox[0] for bbox in bboxes)
    min_y = min(bbox[1] for bbox in bboxes)
    max_x = max(bbox[2] for bbox in bboxes)
    max_y = max(bbox[3] for bbox in bboxes)
    return [min_x, min_y, max_x, max_y]


@click.command(
    short_help="Creates a STAC catalog",
    help="Creates a STAC catalog with the water bodies",
)
@click.option(
    "--input-item",
    "item_urls",
    help="STAC Item URL",
    required=True,
    multiple=True,
)
@click.option(
    "--otsu",
    "otsu",
    help="otsu mask geotiff",
    required=True,
    multiple=True,
)
@click.option(
    "--ndwi",
    "ndwi",
    help="NDWI geotiff",
    required=True,
    multiple=True,
)
def to_stac(item_urls, otsu, ndwi):
    """Creates a STAC catalog with the detected water bodies"""

    logger.info(f"Creating a STAC Catalog for {' '.join(otsu)} and {' '.join(ndwi)}...")
    cat: Catalog = Catalog(id="catalog", description="water-bodies")

    collection_id = "water-bodies"

    out_items = []

    for index, item_url in enumerate(item_urls):
        if os.path.isdir(item_url):
            catalog: Catalog = read_file(os.path.join(item_url, "catalog.json"))
            item: Item = next(catalog.get_items())
        else:
            item: Item = read_file(item_url)

        otsu_mask = otsu[index]
        ndwi_image = ndwi[index]

        asset_path: Path = Path(f"{collection_id}/{item.id}")
        asset_path.mkdir(parents=True, exist_ok=True)
        shutil.copy(otsu_mask, Path(asset_path, os.path.basename(otsu_mask)))
        shutil.copy(ndwi_image, Path(asset_path, "ndwi.tif"))

        # create STAC Item for Otsu mask
        out_item = rio_stac.stac.create_stac_item(
            source=otsu_mask,
            input_datetime=item.datetime,
            id=item.id,
            asset_roles=["data", "visual"],
            asset_href=os.path.basename(otsu_mask),
            asset_name="water-bodies",
            with_proj=True,
            with_raster=True,
        )

        # a temporary item for the ndwi asset
        temp_item = rio_stac.stac.create_stac_item(
            source=str(Path(asset_path, "ndwi.tif")),
            input_datetime=item.datetime,
            id=item.id,
            asset_roles=["data", "visual"],
            asset_href="ndwi.tif",
            asset_name="ndwi",
            with_proj=True,
            with_raster=True,
        )

        # add the ndwi asset to the out_item
        out_item.add_asset(
            "ndwi",
            temp_item.assets["ndwi"],
        )

        out_items.append(out_item)

    logger.info("Creating STAC Collection...")
    # create STAC Collection
    collection: Collection = Collection(
        id=collection_id,
        description="Detected water bodies",
        title="Water bodies",
        extent=Extent(
            spatial=SpatialExtent(bboxes=[get_spatial_extent(out_items)]),
            temporal=TemporalExtent([get_temporal_extent(out_items)]),
        ),
    )

    collection.add_items(out_items)

    collection.item_assets["water-bodies"] = ItemAssetDefinition.create(
        title="Water Bodies",
        description="Water bodies detected",
        roles=["data"],
        media_type=MediaType.COG,
    )

    collection.item_assets["ndwi"] = ItemAssetDefinition.create(
        title="NDWI",
        description="Normalized Difference Water Index",
        roles=["data"],
        media_type=MediaType.COG,
    )

    cat.add_child(collection)
    cat.normalize_and_save(root_href="./", catalog_type=CatalogType.SELF_CONTAINED)
    logger.info("Done!")


if __name__ == "__main__":
    to_stac()
