"""Pin release tools and validate standalone CWL without a packing command."""
import argparse
from pathlib import Path
import re
import yaml
from check_release_cwl import ENTRIES, validate

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--digests", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--version", required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
digests = {}
for path in args.digests.glob("*.txt"):
    reference = path.read_text().strip()
    if not re.fullmatch(r"ghcr\.io/eoap/zarr-cloud-native-format/[\w-]+@sha256:[a-f0-9]{64}", reference):
        raise ValueError(f"Invalid image digest: {path}")
    digests[path.stem] = reference


def pin(value):
    if isinstance(value, dict):
        identifier = value.get("id", "").rsplit("/", 1)[-1].lstrip("#")
        if value.get("class") == "CommandLineTool" and identifier in digests:
            requirements = value.get("requirements", {})
            if isinstance(requirements, list):
                docker = next(item for item in requirements if item.get("class") == "DockerRequirement")
            else:
                docker = requirements["DockerRequirement"]
            docker["dockerPull"] = digests[identifier]
        for key, child in value.items():
            if key == "dockerPull" and "@sha256:" not in child:
                raise ValueError(f"Unpinned image: {child}")
            pin(child)
    elif isinstance(value, list):
        for child in value:
            pin(child)


for name, entry in ENTRIES.items():
    document = yaml.safe_load((Path("cwl-workflow") / f"{name}.cwl").read_text())
    document["s:softwareVersion"] = args.version
    pin(document)
    output = args.output / f"{name}.{args.version}.cwl"
    output.write_text(yaml.safe_dump(document, sort_keys=False))
    validate(output, entry)

from shutil import copyfile
copyfile("cwl-tests/jobs/producer-job.yml", args.output / "producer-job.yaml")
