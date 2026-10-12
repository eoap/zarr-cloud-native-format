"""Expose a completed module-produced Zarr catalog at a stable shared-volume path."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4


def publish(source: Path, destination: Path) -> list[str]:
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise ValueError("Data root must be a directory")
    stores = sorted(source.glob("*/*.zarr"))
    if not stores:
        raise ValueError("Data root must contain <collection>/<item>.zarr stores")
    for store in stores:
        if not store.is_dir() or not (store / "zarr.json").is_file():
            raise ValueError(f"Not a Zarr v3 store: {store}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not destination.is_symlink():
        raise ValueError(f"Refusing to replace existing directory: {destination}")
    if destination.resolve() == source:
        return [str(store.relative_to(source)) for store in stores]
    temporary = destination.with_name(f".{destination.name}-{uuid4().hex}")
    try:
        temporary.symlink_to(source, target_is_directory=True)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return [str(store.relative_to(source)) for store in stores]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--results", type=Path, help="CWL results JSON containing zarr_stac_catalog")
    mode.add_argument(
        "--data-root",
        type=Path,
        help="Completed catalog root containing collection directories",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "titiler-data",
    )
    args = parser.parse_args()
    try:
        source = args.data_root
        if args.results:
            result = json.loads(args.results.read_text())["zarr_stac_catalog"]
            location = result.get("location") or result.get("path")
            if not location:
                raise ValueError("Missing zarr_stac_catalog.location/path")
            parsed = urlsplit(location)
            if parsed.scheme not in ("", "file") or parsed.netloc not in (
                "",
                "localhost",
            ):
                raise ValueError("Publication requires a local filesystem catalog")
            source = Path(unquote(parsed.path))
            if not source.is_absolute():
                source = Path.cwd() / source
        stores = publish(source, args.destination)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Cannot publish TiTiler store: {error}\n")
    print(
        json.dumps(
            {
                "data_root": str(source.resolve()),
                "published_path": str(args.destination),
                "stores": stores,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
