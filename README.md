# zarr-cloud-native-format



cwltool --parallel \
    /data/work/eoap/zarr-cloud-native-format/cwl-workflow/app-water-bodies.cwl#water-bodies \
    --stac_items "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a-cogs/items/S2A_10TFK_20210708_0_L2A" \
    --stac_items "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a-cogs/items/S2B_10TFK_20210713_0_L2A" \
    --stac_items "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a-cogs/items/S2B_10TFK_20210723_0_L2A" \
    --aoi="-121.399,39.834,-120.74,40.472" \
    --epsg "EPSG:4326" \
    --bands green \
    --bands nir


cwltool --parallel \
    https://github.com/eoap/zarr-cloud-native-format/releases/download/0.1.0/app-water-bodies.0.1.0.cwl#water-bodies \
    --stac_items "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a-cogs/items/S2A_10TFK_20210708_0_L2A" \
    --stac_items "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a-cogs/items/S2B_10TFK_20210713_0_L2A" \
    --stac_items "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a-cogs/items/S2B_10TFK_20210723_0_L2A" \
    --aoi="-121.399,39.834,-120.74,40.472" \
    --epsg "EPSG:4326" \
    --bands green \
    --bands nir
