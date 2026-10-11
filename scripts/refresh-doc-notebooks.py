"""Refresh producer documentation notebooks, skipping the user store example."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="*", type=Path)
    args = parser.parse_args()
    paths = [
        *sorted((ROOT / "docs/cwl-cli").glob("*.ipynb")),
        ROOT / "docs/sub-workflow/water-bodies-detection.ipynb",
        ROOT / "docs/cwl-workflows/producer.ipynb",
    ]
    if args.notebooks:
        paths = [path.resolve() for path in args.notebooks]
    with tempfile.TemporaryDirectory(prefix="eoap-docs-kernel-") as directory:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ipykernel",
                "install",
                "--prefix",
                directory,
                "--name",
                "eoap-docs",
            ],
            check=True,
        )
        os.environ["JUPYTER_PATH"] = str(Path(directory) / "share/jupyter")
        for path in paths:
            print("Refreshing", path.relative_to(ROOT), flush=True)
            notebook = nbformat.read(path, as_version=4)
            NotebookClient(
                notebook,
                timeout=180,
                kernel_name="eoap-docs",
                resources={"metadata": {"path": str(path.parent)}},
            ).execute()
            for cell in notebook.cells:
                if any(output.output_type == "error" for output in cell.get("outputs", [])):
                    raise RuntimeError(f"Notebook display failed: {path}")
            nbformat.validate(notebook)
            nbformat.write(notebook, path)
            print("Saved", path.relative_to(ROOT), flush=True)


if __name__ == "__main__":
    main()
