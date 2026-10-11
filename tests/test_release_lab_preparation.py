"""Prevent labs from accepting mismatched or local release artifacts."""
import importlib.util
from pathlib import Path
from copy import deepcopy
import pytest

spec = importlib.util.spec_from_file_location('prepare_labs', Path(__file__).parents[1] / 'scripts/prepare-practice-labs.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

@pytest.fixture
def package():
    return {'cwlVersion':'v1.2','s:softwareVersion':'2.0.0-rc.1.1','$graph':[{'id':'water-bodies','class':'Workflow'},{'id':'crop','class':'CommandLineTool','requirements':{'DockerRequirement':{'dockerPull':'ghcr.io/eoap/zarr-cloud-native-format/crop@sha256:'+'a'*64}}}]}

def test_matching_candidate(package):
    module.check_package(package,'2.0.0-rc.1.1','water-bodies')

@pytest.mark.parametrize('version,entry', [('2.0.0','water-bodies'),('2.0.0-rc.1.1','main')])
def test_mismatched_release_or_entrypoint(package,version,entry):
    with pytest.raises(ValueError): module.check_package(package,version,entry)

@pytest.mark.parametrize('image',['crop:latest','ghcr.io/eoap/zarr-cloud-native-format/crop:latest','localhost:5000/crop@sha256:'+'a'*64])
def test_unpublished_or_mutable_image(package,image):
    package['$graph'][1]['requirements']['DockerRequirement']['dockerPull']=image
    with pytest.raises(ValueError): module.check_package(package,'2.0.0-rc.1.1','water-bodies')

def test_failed_download_validation_preserves_prepared_files(package,tmp_path,monkeypatch):
    import io
    import yaml
    destination=tmp_path/'packages'
    destination.mkdir()
    previous=destination/'app-water-bodies.cwl'
    previous.write_text('previous validated package')
    wrong=deepcopy(package)
    wrong['s:softwareVersion']='0.5.0'
    monkeypatch.setattr(module,'urlopen',lambda *args,**kwargs:io.BytesIO(yaml.safe_dump(wrong).encode()))
    with pytest.raises(ValueError): module.prepare('2.0.0-rc.1.1',destination)
    assert previous.read_text()=='previous validated package'
    assert not (destination/'release.json').exists()
