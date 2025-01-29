import json
import os

import pytest

from leapp.libraries.actor import scandefinedipupaths
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.models import IPUPath, IPUPaths
from leapp.utils.deprecation import suppress_deprecation

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class CurrentActorMockedModified(CurrentActorMocked):
    def get_common_file_path(self, fname):
        fpath = os.path.join(CUR_DIR, 'files', fname)
        assert os.path.exists(fpath)
        if os.path.exists(fpath):
            return fpath
        return None


@pytest.mark.parametrize(('flavour', 'expected_result'), (
    ('nonsense', {}),
    (
        'default',
        {
            '8.10': ['9.4', '9.5', '9.6'],
            '8.4': ['9.2'],
            '9.6': ['10.0'],
            '8': ['9.4', '9.5', '9.6'],
            '9': ['10.0']
        }
    ),
    (
        'saphana',
        {
            '8.10': ['9.6', '9.4'],
            '8': ['9.6', '9.4'],
            '9.6': ['10.0'],
            '9': ['10.0']
        }
    ),
))
def test_load_ipu_paths_for_flavour(monkeypatch, flavour, expected_result):
    monkeypatch.setattr(scandefinedipupaths.api, 'current_actor', CurrentActorMockedModified())

    result = scandefinedipupaths.load_ipu_paths_for_flavour(flavour=flavour)
    assert result == expected_result


_DATA_IPU_PATHS = {
    '8.10': ['9.4', '9.5', '9.6'],
    '8.4': ['9.2'],
    '9.6': ['10.0'],
    '8': ['9.4', '9.5', '9.6'],
    '80.0': ['81.0']
}


@suppress_deprecation(IPUPaths)
@pytest.mark.parametrize(('maj_version', 'expected_result'), (
    ('7', []),
    (
        '8',
        [
            IPUPath(source_version='8.10', target_versions=['9.4', '9.5', '9.6']),
            IPUPath(source_version='8.4', target_versions=['9.2']),
            IPUPath(source_version='8', target_versions=['9.4', '9.5', '9.6']),
        ]
    ),
    (
        '80',
        [
            IPUPath(source_version='80.0', target_versions=['81.0']),
        ]
    ),


))
def test_get_filtered_ipu_paths(monkeypatch, maj_version, expected_result):
    result = scandefinedipupaths.get_filtered_ipu_paths(_DATA_IPU_PATHS, maj_version)
    result = sorted(result, key=lambda x: x.source_version)
    assert result == sorted(expected_result, key=lambda x: x.source_version)


def test_scan_defined_ipu_paths(monkeypatch):
    # let's try one 'full' happy run
    monkeypatch.setattr(scandefinedipupaths.api, 'current_actor', CurrentActorMockedModified(src_ver='9.6'))
    monkeypatch.setattr(scandefinedipupaths.api, 'produce', produce_mocked())
    scandefinedipupaths.process()

    assert scandefinedipupaths.api.produce.called == 1
    msg = scandefinedipupaths.api.produce.model_instances[0]
    assert isinstance(msg, IPUPaths)
    assert len(msg.data) == 2
    assert {i.source_version for i in msg.data} == {'9', '9.6'}
