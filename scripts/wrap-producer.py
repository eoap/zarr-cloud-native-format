"""Compose a producer and the mastering stage-out tool using eoap-cwlwrap."""

import argparse
import json
import os
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import yaml
from cwl_loader import load_cwl_from_location, dump_cwl
from cwl_loader.utils import search_process
from eoap_cwlwrap import wrap
import cwl_loader
import eoap_cwlwrap
import sys

cwl_loader.logger.remove()
cwl_loader.logger.add(sys.stderr, level="INFO")
eoap_cwlwrap.logger.remove()
eoap_cwlwrap.logger.add(sys.stderr, level="INFO")

parser = argparse.ArgumentParser(description=__doc__)
root = Path(__file__).resolve().parents[1]
parser.add_argument(
    "--workflow", type=Path, default=root / "cwl-workflow/app-water-bodies.cwl"
)
parser.add_argument("--entrypoint", default="water-bodies")
parser.add_argument("--stage-out", type=Path, default=root / "cwl-cli/stage-out.cwl")
settings_path = root / ".publication-settings.json"
settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
parser.add_argument(
    "--image",
    default=os.environ.get(
        "STAGE_OUT_IMAGE", settings.get("stageOutImage", "eoap-zarr-stage-out:local")
    ),
)
parser.add_argument(
    "--output", type=Path, default=root / "cwl-workflow/app-water-bodies-s3.cwl"
)
args = parser.parse_args()
loaded = load_cwl_from_location(path=str(args.workflow))
workflow = search_process(process_id=args.entrypoint, process=loaded)
if workflow is None:
    parser.error("Workflow entrypoint was not found")
# The wrapped producer is intended for STAC API item publication.
for parameter in workflow.inputs:
    if parameter.id.rsplit("/", 1)[-1] == "stac_object_type":
        parameter.default = "item"
# Only stage the final GeoZarr catalog; intermediate outputs would duplicate
# wrapper parameters and publish unrelated data under the same S3 prefix.
workflow.outputs = [
    port
    for port in workflow.outputs
    if port.id.rsplit("/", 1)[-1] == "zarr_stac_catalog"
]
if len(workflow.outputs) != 1:
    parser.error("Workflow must expose zarr_stac_catalog")
stage = yaml.safe_load(args.stage_out.read_text())
stage["requirements"]["DockerRequirement"]["dockerPull"] = args.image
with TemporaryDirectory() as directory:
    path = Path(directory) / "stage-out.cwl"
    path.write_text(yaml.safe_dump(stage, sort_keys=False))
    stage_process = load_cwl_from_location(path=str(path))
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
# Preserve shared OGC imports; only embed the wrapper's own URI record.
uri = {
    "name": "https://raw.githubusercontent.com/eoap/schemas/main/string_format.yaml#URI",
    "type": "record",
    "fields": [{"name": "value", "type": "string", "doc": "Resource URI."}],
}


def embed(value):
    if isinstance(value, dict):
        if (
            value.get("$import")
            == "https://raw.githubusercontent.com/eoap/schemas/main/string_format.yaml"
        ):
            return [deepcopy(uri)]
        return {k: embed(v) for k, v in value.items()}
    if isinstance(value, list):
        result = []
        for entry in value:
            child = embed(entry)
            result.extend(child) if isinstance(child, list) else result.append(child)
        return result
    return value


document = embed(yaml.safe_load(args.output.read_text()))
# Parser serialization embeds the module schemas in the generated document.
# The original source CWL and its shared schema imports are left unchanged.
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
