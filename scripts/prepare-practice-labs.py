"""Download and validate matching release packages and inputs for the labs."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen
import yaml

PACKAGES = {
    'app-water-bodies': 'water-bodies',
    'app-water-bodies-s3': 'main',
    'app-water-bodies-occurrence': 'water-bodies-occurrence',
}


def check_package(document, version, entry):
    if document.get('cwlVersion') != 'v1.2' or document.get('s:softwareVersion') != version:
        raise ValueError('Package CWL/release version does not match the selected release')
    if not any(p.get('id', '').lstrip('#') == entry and p.get('class') == 'Workflow' for p in document.get('$graph', [])):
        raise ValueError(f'Missing Workflow entrypoint #{entry}')
    images = []
    def walk(value):
        if isinstance(value, dict):
            if 'dockerPull' in value:
                images.append(value['dockerPull'])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(document)
    if not images:
        raise ValueError('Package has no container references')
    for image in images:
        if not re.fullmatch(r'ghcr\.io/eoap/.+@sha256:[a-f0-9]{64}', image):
            raise ValueError(f'Expected a published digest-pinned image: {image}')


def prepare(version, destination):
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', version):
        raise ValueError('Invalid release version')
    destination.mkdir(parents=True, exist_ok=True)
    base = f'https://github.com/eoap/zarr-cloud-native-format/releases/download/{version}'
    with TemporaryDirectory(dir=destination) as directory:
        staging = Path(directory)
        for name, entry in PACKAGES.items():
            with urlopen(f'{base}/{name}.{version}.cwl', timeout=120) as response:
                content = response.read()
            path = staging / f'{name}.cwl'
            path.write_bytes(content)
            check_package(yaml.safe_load(content), version, entry)
            subprocess.run(['cwltool', '--validate', f'{path}#{entry}'], check=True)
        with urlopen(f'{base}/producer-job.yaml', timeout=120) as response:
            (staging / 'producer-job.yaml').write_bytes(response.read())
        subprocess.run(['cwltool', '--validate', f'{staging}/app-water-bodies.cwl#water-bodies', str(staging / 'producer-job.yaml')], check=True)
        # Publish prepared files only after every package and the inputs pass.
        for path in staging.iterdir():
            path.replace(destination / path.name)
        (destination / 'release.json').write_text(json.dumps({'version': version, 'packages': PACKAGES}, indent=2)+'\n')
    print(f'Prepared practice labs for {version} at {destination}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.version, args.destination)
