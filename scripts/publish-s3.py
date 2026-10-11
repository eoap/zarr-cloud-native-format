"""Stage a completed catalog with an eoap-cwlwrap workflow, then index it."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import yaml

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
mode = parser.add_mutually_exclusive_group(required=True)
mode.add_argument("--data-root", type=Path)
mode.add_argument("--results", type=Path)
parser.add_argument("--prefix", default=None)
args = parser.parse_args()
settings = json.load(sys.stdin)
run = Path("/calrissian") / f"zarr-publication-{uuid4().hex}"
run.mkdir()
prefix = args.prefix or f"zarr/{run.name}"
source = args.data_root
if args.results:
    value = json.loads(args.results.read_text())["zarr_stac_catalog"]
    if isinstance(value, dict) and "value" in value:
        catalog = value["value"]
        source = None
    else:
        from urllib.parse import unquote, urlsplit

        source = Path(unquote(urlsplit(value.get("location") or value["path"]).path))
if source is not None:
    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client(
        "s3",
        endpoint_url=settings["endpoint"],
        aws_access_key_id=settings["accessKey"],
        aws_secret_access_key=settings["secretKey"],
        region_name=settings["region"],
    )
    try:
        client.head_bucket(Bucket=settings["bucket"])
    except ClientError as error:
        if error.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
            raise
        options = {"Bucket": settings["bucket"]}
        if settings["region"] != "us-east-1":
            options["CreateBucketConfiguration"] = {"LocationConstraint": settings["region"]}
        client.create_bucket(**options)
    source = source.resolve(strict=True)
    workflow = {
        "cwlVersion": "v1.2",
        "class": "Workflow",
        "id": "publish-outputs",
        "label": "Publish completed GeoZarr outputs",
        "doc": "Pass completed local module outputs to the mastering stage-out tool.",
        "inputs": [],
        "outputs": [
            {
                "id": "zarr_stac_catalog",
                "type": "Directory",
                "outputSource": "catalog/directory",
            }
        ],
        "steps": [
            {
                "id": "catalog",
                "in": [],
                "out": ["directory"],
                "run": {
                    "class": "ExpressionTool",
                    "inputs": [],
                    "outputs": [
                        {
                            "id": "directory",
                            "type": "Directory",
                            "doc": "Completed STAC and Zarr output directory.",
                        }
                    ],
                    "requirements": {"InlineJavascriptRequirement": {}},
                    "expression": '${ return {directory: {class: "Directory", location: '
                    + json.dumps(source.as_uri())
                    + "}}; }",
                },
            }
        ],
    }
    original = run / "publication.cwl"
    original.write_text(yaml.safe_dump(workflow, sort_keys=False))
    wrapped = run / "publication-s3.cwl"
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts/wrap-producer.py"),
            "--workflow",
            str(original),
            "--entrypoint",
            "publish-outputs",
            "--image",
            settings["stageOutImage"],
            "--output",
            str(wrapped),
        ],
        check=True,
    )
    job = {
        "s3_bucket": settings["bucket"],
        "sub_path": prefix,
        "aws_access_key_id": settings["accessKey"],
        "aws_secret_access_key": settings["secretKey"],
        "region_name": settings["region"],
        "endpoint_url": settings["endpoint"],
    }
    parameters = run / "parameters.json"
    parameters.write_text(json.dumps(job))
    parameters.chmod(0o600)
    result = run / "results.json"
    try:
        with result.open("w") as stream:
            environment = os.environ.copy()
            environment.pop("CWLTOOL_OPTIONS", None)
            subprocess.run(
                [
                    "/opt/calrissian-venv/bin/calrissian",
                    "--max-cores",
                    "2",
                    "--max-ram",
                    "2G",
                    "--tmp-outdir-prefix",
                    str(run / "tmp"),
                    "--outdir",
                    str(run / "outputs"),
                    "--pod-nodeselectors",
                    "/etc/calrissian/pod-node-selector.yaml",
                    str(wrapped),
                    str(parameters),
                ],
                stdout=stream,
                env=environment,
                check=True,
            )
    finally:
        parameters.unlink(missing_ok=True)
    catalog = json.loads(result.read_text())["zarr_stac_catalog"]["value"]
environment = os.environ.copy()
environment.update(
    aws_endpoint_url=settings["endpoint"],
    aws_access_key_id=settings["accessKey"],
    aws_secret_access_key=settings["secretKey"],
    aws_region_name=settings["region"],
)
subprocess.run(
    [sys.executable, str(root / "scripts/index-s3-catalog.py"), catalog],
    env=environment,
    check=True,
)
print(catalog)
