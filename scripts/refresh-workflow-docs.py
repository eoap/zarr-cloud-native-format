"""Regenerate CWL documentation and render its diagrams locally with PlantUML."""

import os
import subprocess
import tempfile
from io import StringIO
from pathlib import Path

from cwl2puml import DiagramType, to_puml
from cwl_loader import load_cwl_from_location
from eoap_http import read_https

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    cwl = ROOT / "cwl-workflow/app-water-bodies.cwl"
    docs = ROOT / "docs/design"
    subprocess.run(
        [
            "transpiler-mate",
            "markdown",
            "--workflow-id",
            "water-bodies",
            "--output",
            str(docs),
            "--code-repository",
            "https://github.com/eoap/zarr-cloud-native-format.git",
            str(cwl),
        ],
        check=True,
    )
    path = docs / "water-bodies.md"
    text = path.read_text().replace("--consolidate <CONSOLIDATE>", "--consolidate")
    text = text.replace("--titiler-eopf-compatible <TITILER_EOPF_COMPATIBLE> \\\n", "")
    text = text.replace("(--resolution <RESOLUTION>) \\\n", "")
    text += """
## Execution and validation notes

The package uses CWL v1.2. Docker declarations are execution requirements.
Build local images with `task containers:build:producer`. Select `#water-bodies`
when validating or running the package, because it also contains a subworkflow.

CLI examples use placeholders for values. Optional resolution can be set with
`--resolution <RESOLUTION>`. `--consolidate` is a flag; use `--no-consolidate`
to disable consolidation. The deprecated `--titiler-eopf-compatible` flag takes
no value and does not suppress GeoZarr metadata.

`stac-zarr` writes the published Pilot `v0.1` proj, spatial, and multiscales
conventions. It validates the completed store with the GeoZarr Toolkit Python API
before writing STAC output and consolidating metadata. Each measurement and
overview array declares its own projection and spatial metadata. Invalid stores
raise an error; partial files can remain on disk after failure.

Validate existing stores with `stac-zarr-validate /absolute/path/to/output.zarr`.
See [GeoZarr compliance](../compliance/geozarr-minispec-compliance.md) for the
validation scope and [CLI usage](../how-to/stac-zarr-usage.md) for runnable examples.
"""
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n")
    jar = Path(
        os.environ.get("PLANTUML_JAR", str(Path(tempfile.gettempdir()) / "eoap-plantuml.jar"))
    )
    if not jar.is_file():
        url = "https://repo.maven.apache.org/maven2/net/sourceforge/plantuml/plantuml/1.2025.10/plantuml-1.2025.10.jar"
        jar.write_bytes(read_https(url))
    processes = load_cwl_from_location(path=str(cwl))
    for workflow in ("water-bodies", "detect_water_body"):
        folder = docs / workflow
        folder.mkdir(parents=True, exist_ok=True)
        for kind in DiagramType:
            output = StringIO()
            to_puml(processes, kind, output, workflow_id=workflow)
            source = output.getvalue().replace("@startuml", "@startuml\n!pragma layout smetana", 1)
            result = subprocess.run(
                [
                    "java",
                    "-Djava.awt.headless=true",
                    "-jar",
                    str(jar),
                    "-pipe",
                    "-tsvg",
                ],
                input=source.encode(),
                capture_output=True,
                check=True,
            )
            if b"<svg" not in result.stdout:
                raise ValueError(f"Invalid SVG for {workflow}/{kind.name}")
            (folder / (kind.name.lower() + ".svg")).write_bytes(result.stdout)
            print(f"Refreshed {workflow}/{kind.name.lower()}.svg", flush=True)


if __name__ == "__main__":
    main()
