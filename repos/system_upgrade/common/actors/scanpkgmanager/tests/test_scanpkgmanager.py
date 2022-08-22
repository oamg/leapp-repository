import os

import pytest

from leapp.libraries import stdlib
from leapp.libraries.actor import scanpkgmanager
from leapp.libraries.common import testutils
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def mock_releasever_exists(overrides):
    def mocked_releasever_exists(name):
        if name in overrides:
            return overrides[name]
        raise ValueError
    return mocked_releasever_exists


def mocked_get_releasever_path():
    return os.path.join(CUR_DIR, 'files/releasever')


@pytest.mark.parametrize('etcrelease_exists', [True, False])
def test_get_etcreleasever(monkeypatch, etcrelease_exists):
    monkeypatch.setattr(
        scanpkgmanager,
        '_releasever_exists', mock_releasever_exists(
            {
                os.path.join(CUR_DIR, 'files/releasever'): etcrelease_exists,
            }
        )
    )
    monkeypatch.setattr(scanpkgmanager.api, 'produce', produce_mocked())
    monkeypatch.setattr(scanpkgmanager.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(scanpkgmanager, '_get_releasever_path', mocked_get_releasever_path)

    scanpkgmanager.process()

    assert scanpkgmanager.api.produce.called
    if etcrelease_exists:
        assert api.produce.model_instances[0].etc_releasever
    else:
        assert not api.produce.model_instances[0].etc_releasever
