"""Validate each standalone application package using its public entrypoint."""
from pathlib import Path
import subprocess
import yaml

ENTRIES = {"app-water-bodies": "water-bodies", "app-water-bodies-s3": "main"}


def validate(path, entry):
    document = yaml.safe_load(path.read_text())
    if document.get("cwlVersion") != "v1.2":
        raise ValueError(f"Expected CWL v1.2: {path}")
    if entry not in {process.get("id") for process in document["$graph"]}:
        raise ValueError(f"Missing entrypoint {entry}: {path}")
    subprocess.run(["cwltool", "--validate", f"{path}#{entry}"], check=True)


if __name__ == "__main__":
    for name, entry in ENTRIES.items():
        validate(Path("cwl-workflow") / f"{name}.cwl", entry)
