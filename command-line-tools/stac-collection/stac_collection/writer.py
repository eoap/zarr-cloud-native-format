import os
import shutil
from pathlib import Path

import rio_stac
from loguru import logger
from pystac import (
    Catalog,
    CatalogType,
    Collection,
    Extent,
    Item,
    SpatialExtent,
    TemporalExtent,
    read_file,
)
from pystac.extensions.render import Render, RenderExtension
from pystac.item_assets import ItemAssetDefinition
from pystac.media_type import MediaType

from stac_collection.contract import get_spatial_extent, get_temporal_extent, validate_parallel_inputs


def _read_input_item(item_url: str) -> Item:
    if os.path.isdir(item_url):
        catalog: Catalog = read_file(os.path.join(item_url, "catalog.json"))
        return next(catalog.get_items())
    return read_file(item_url)


def run_to_stac(
    item_urls: tuple[str, ...],
    otsu: tuple[str, ...],
    ndwi: tuple[str, ...],
    output_dir: Path = Path("."),
) -> None:
    """Create a STAC catalog for the Otsu and NDWI outputs."""
    validate_parallel_inputs(item_urls, otsu, ndwi)

    logger.info(f"Creating a STAC Catalog for {' '.join(otsu)} and {' '.join(ndwi)}...")
    cat: Catalog = Catalog(id="catalog", description="water-bodies")

    collection_id = "water-bodies"
    out_items = []

    output_dir.mkdir(parents=True, exist_ok=True)

    for index, item_url in enumerate(item_urls):
        item = _read_input_item(item_url)
        otsu_mask = otsu[index]
        ndwi_image = ndwi[index]

        asset_path: Path = output_dir / collection_id / item.id
        asset_path.mkdir(parents=True, exist_ok=True)
        shutil.copy(otsu_mask, asset_path / os.path.basename(otsu_mask))
        shutil.copy(ndwi_image, asset_path / "ndwi.tif")

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

        temp_item = rio_stac.stac.create_stac_item(
            source=str(asset_path / "ndwi.tif"),
            input_datetime=item.datetime,
            id=item.id,
            asset_roles=["data", "visual"],
            asset_href="ndwi.tif",
            asset_name="ndwi",
            with_proj=True,
            with_raster=True,
        )

        out_item.add_asset("ndwi", temp_item.assets["ndwi"])
        out_items.append(out_item)

    logger.info("Creating STAC Collection...")
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

    # Provide default rendering profiles for discovery/visualization clients.
    render_ext = RenderExtension.ext(collection, add_if_missing=True)
    render_ext.renders = {
        "ndwi": Render.create(
            assets=["ndwi"],
            title="NDWI",
            rescale=[[-1, 1]],
            colormap_name="viridis",
        ),
        "water-bodies": Render.create(
            assets=["water-bodies"],
            title="Water Bodies",
            # LUT-style colormap: transparent background, detected water in blue.
            colormap={
                "0": [0, 0, 0, 0],
                "1": [0, 0, 255, 255],
                "255": [0, 0, 255, 255],
            },
        ),
    }

    cat.add_child(collection)
    cat.normalize_and_save(root_href=str(output_dir), catalog_type=CatalogType.SELF_CONTAINED)
    logger.info("Done!")
