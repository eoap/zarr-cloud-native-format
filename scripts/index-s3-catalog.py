"""Build a STAC GeoParquet index from a completed S3 catalog publication."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit
from uuid import uuid4
import boto3
import pystac
import rustac
from pystac.stac_io import DefaultStacIO

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("catalog")
parser.add_argument(
    "--index-dir",
    type=Path,
    default=Path(__file__).resolve().parents[1] / "titiler-index",
)
args = parser.parse_args()
client = boto3.client(
    "s3",
    endpoint_url=os.environ["aws_endpoint_url"],
    aws_access_key_id=os.environ["aws_access_key_id"],
    aws_secret_access_key=os.environ["aws_secret_access_key"],
    region_name=os.environ.get("aws_region_name", "us-east-1"),
)


class S3IO(DefaultStacIO):
    def read_text(self, source, *a, **kw):
        parsed = urlsplit(str(source))
        if parsed.scheme == "s3":
            return (
                client.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip("/"))[
                    "Body"
                ]
                .read()
                .decode()
            )
        return super().read_text(source, *a, **kw)


catalog = pystac.Catalog.from_file(args.catalog, stac_io=S3IO())
items = list(catalog.get_items(recursive=True))
if not items:
    parser.error("Publication requires item-mode STAC outputs")
# One output collection per index, matching the lightweight backend contract.
collection_id = catalog.id
for item in items:
    item.collection_id = collection_id
    for asset in item.assets.values():
        if not asset.href.startswith("s3://"):
            parser.error("Asset references must be S3 URLs")
    # Root-relative viewer URLs work with port forwarding and an Ingress alike.
    route = f"/api/collections/{quote(collection_id, safe='')}/items/{quote(item.id, safe='')}/assets/measurements"
    item.links = [link for link in item.links if not link.extra_fields.get("eoap:viewer")]
    for variable, rescale, colormap in (("ndwi", "-1,1", "viridis"), ("water-bodies", "0,1", "blues")):
        query = urlencode({"variables": variable, "rescale": rescale, "colormap_name": colormap, "bidx": 1})
        item.add_link(pystac.Link(
            "tilejson", f"{route}/WebMercatorQuad/tilejson.json?{query}",
            media_type="application/json", title=f"{variable} TileJSON",
            extra_fields={"eoap:viewer": True},
        ))
    # Keep the staged source Item and the API index consistent.
    source = urlsplit(item.get_self_href())
    if source.scheme != "s3":
        parser.error("Published Item metadata must have an S3 self URL")
    client.put_object(Bucket=source.netloc, Key=source.path.lstrip("/"),
                      Body=json.dumps(item.to_dict()).encode(), ContentType="application/geo+json")
index = args.index_dir
index.mkdir(parents=True, exist_ok=True)
version = uuid4().hex
path = index / f"{collection_id}-{version}.parquet"
rustac.write_sync(
    str(path),
    {"type": "FeatureCollection", "features": [item.to_dict() for item in items]},
    format="geoparquet",
)
collection = pystac.Collection(
    collection_id,
    catalog.description,
    pystac.Extent.from_items(items),
    title=catalog.title,
)
collection.extra_fields["renders"] = items[0].properties.get("renders", {})
collection.extra_fields["summaries"] = {
    "datetime": items[0]
    .assets["measurements"]
    .extra_fields.get("cube:dimensions", {})
    .get("time", {})
    .get("values", [])
}
collection.add_asset(
    "index",
    pystac.Asset(
        str(path), media_type="application/vnd.apache.parquet", roles=["metadata"]
    ),
)
manifest = index / "collections.json"
existing = json.loads(manifest.read_text()) if manifest.exists() else []
collections = [entry for entry in existing if entry["id"] != collection_id] + [
    collection.to_dict()
]
# Retain a portable metadata index alongside the staged catalog in S3.
parsed = urlsplit(args.catalog)
key = parsed.path.lstrip("/").rsplit("/", 1)[0] + "/items.parquet"
client.upload_file(str(path), parsed.netloc, key)
temporary = index / f".collections-{version}.json"
temporary.write_text(json.dumps(collections))
os.replace(temporary, manifest)
print(
    json.dumps(
        {
            "collection": collection_id,
            "items": len(items),
            "index": str(path),
            "s3_index": f"s3://{parsed.netloc}/{key}",
        }
    )
)
