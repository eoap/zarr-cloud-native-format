"""Compose a producer and the mastering stage-out tool using eoap-cwlwrap."""

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from cwl_loader import dump_cwl, load_cwl_from_location
from cwl_loader.utils import search_process
from cwl_utils.parser.cwl_v1_2 import CommandLineTool, Workflow
from eoap_cwlwrap import wrap
from loguru import logger
from shared_schema_imports import restore_published_schemas

logger.remove()
logger.add(sys.stderr, level="INFO")

parser = argparse.ArgumentParser(description=__doc__)
root = Path(__file__).resolve().parents[1]
parser.add_argument("--workflow", type=Path, default=root / "cwl-workflow/app-water-bodies.cwl")
parser.add_argument("--entrypoint", default="water-bodies")
parser.add_argument("--stage-out", type=Path, default=root / "cwl-cli/stage-out.cwl")
settings_path = root / ".publication-settings.json"
settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
parser.add_argument(
    "--image",
    default=os.environ.get(
        "STAGE_OUT_IMAGE",
        settings.get(
            "stageOutImage",
            "ghcr.io/eoap/mastering-app-package/stage-out:2.0.0@sha256:2974b42df1722ebf4d220c041e4345a94553b1bb81188b545fd58c70e93f490a",
        ),
    ),
)
parser.add_argument("--output", type=Path, default=root / "cwl-workflow/app-water-bodies-s3.cwl")
args = parser.parse_args()
loaded = load_cwl_from_location(path=str(args.workflow))
workflow = search_process(process_id=args.entrypoint, process=loaded)
if not isinstance(workflow, Workflow):
    parser.error("A CWL v1.2 Workflow entrypoint is required")
# The wrapped producer is intended for STAC API item publication.
for parameter in workflow.inputs:
    if parameter.id.rsplit("/", 1)[-1] == "stac_object_type":
        parameter.default = "item"
# Only stage the final GeoZarr catalog; intermediate outputs would duplicate
# wrapper parameters and publish unrelated data under the same S3 prefix.
workflow.outputs = [
    port for port in workflow.outputs if port.id.rsplit("/", 1)[-1] == "zarr_stac_catalog"
]
if len(workflow.outputs) != 1:
    parser.error("Workflow must expose zarr_stac_catalog")
stage = yaml.safe_load(args.stage_out.read_text())
stage["requirements"]["DockerRequirement"]["dockerPull"] = args.image
with TemporaryDirectory() as directory:
    path = Path(directory) / "stage-out.cwl"
    path.write_text(yaml.safe_dump(stage, sort_keys=False))
    stage_process = load_cwl_from_location(path=str(path))
    if not isinstance(stage_process, CommandLineTool):
        parser.error("Stage-out must be a CWL v1.2 CommandLineTool")
    wrapped = wrap(workflow=workflow, directory_stage_out=stage_process)
    with args.output.open("w") as stream:
        dump_cwl(
            process=[
                wrapped,
                *(loaded if isinstance(loaded, list) else [loaded]),
                stage_process,
            ],
            stream=stream,
        )
# Preserve the published shared schema imports emitted by the wrapper.
# Module-owned definitions are already embedded in the standalone source CWL.
document = yaml.safe_load(args.output.read_text())
restore_published_schemas(document)
document["cwlVersion"] = "v1.2"
metadata = yaml.safe_load(args.workflow.read_text())
for key in (
    "$namespaces",
    "s:name",
    "s:description",
    "s:softwareVersion",
    "s:license",
    "s:author",
    "s:codeRepository",
):
    if key in metadata:
        document[key] = deepcopy(metadata[key])
args.output.write_text(yaml.safe_dump(document, sort_keys=False))
print(args.output)
