"""Download and validate matching release packages and inputs for the labs."""

import argparse
import json
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from eoap_http import read_https

PACKAGES = {
    "app-water-bodies": "water-bodies",
    "app-water-bodies-s3": "main",
    "app-water-bodies-occurrence": "water-bodies-occurrence",
}


def container_images(value: object) -> list[str]:
    """Collect image references without trusting malformed document values."""
    images: list[str] = []
    if isinstance(value, dict):
        if "dockerPull" in value:
            image = value["dockerPull"]
            if not isinstance(image, str):
                raise ValueError("Container reference must be a string")
            images.append(image)
        for child in value.values():
            images.extend(container_images(child))
    elif isinstance(value, list):
        for child in value:
            images.extend(container_images(child))
    return images


def check_package(document: dict[str, object], version: str, entry: str) -> None:
    if document.get("cwlVersion") != "v1.2" or document.get("s:softwareVersion") != version:
        raise ValueError("Package CWL/release version does not match the selected release")
    graph = document.get("$graph", [])
    if not isinstance(graph, list):
        raise ValueError("Package graph must be a list")
    workflows = [p for p in graph if isinstance(p, dict) and p.get("class") == "Workflow"]
    if not any(str(p.get("id", "")).lstrip("#") == entry for p in workflows):
        raise ValueError(f"Missing Workflow entrypoint #{entry}")
    images = container_images(document)
    if not images:
        raise ValueError("Package has no container references")
    for image in images:
        if not re.fullmatch(r"ghcr\.io/eoap/.+@sha256:[a-f0-9]{64}", image):
            raise ValueError(f"Expected a published digest-pinned image: {image}")


def download(url: str) -> bytes:
    """Download a published artifact using HTTPS only."""
    return read_https(url, timeout=120)


def prepare(version: str, destination: Path) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        raise ValueError("Invalid release version")
    destination.mkdir(parents=True, exist_ok=True)
    base = f"https://github.com/eoap/zarr-cloud-native-format/releases/download/{version}"
    with TemporaryDirectory(dir=destination) as directory:
        staging = Path(directory)
        for name, entry in PACKAGES.items():
            content = download(f"{base}/{name}.{version}.cwl")
            path = staging / f"{name}.cwl"
            path.write_bytes(content)
            check_package(yaml.safe_load(content), version, entry)
            subprocess.run(["cwltool", "--validate", f"{path}#{entry}"], check=True)
        (staging / "producer-job.yaml").write_bytes(download(f"{base}/producer-job.yaml"))
        subprocess.run(
            [
                "cwltool",
                "--validate",
                f"{staging}/app-water-bodies.cwl#water-bodies",
                str(staging / "producer-job.yaml"),
            ],
            check=True,
        )
        # Publish prepared files only after every package and the inputs pass.
        for path in staging.iterdir():
            path.replace(destination / path.name)
        (destination / "release.json").write_text(
            json.dumps({"version": version, "packages": PACKAGES}, indent=2) + "\n"
        )
    print(f"Prepared practice labs for {version} at {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.version, args.destination)
