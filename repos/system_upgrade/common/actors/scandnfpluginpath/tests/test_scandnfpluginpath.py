import pytest

from leapp.libraries.actor.scandnfpluginpath import scan_dnf_pluginpath
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DnfPluginPathDetected


@pytest.mark.parametrize('is_detected', [False, True])
def test_scan_detects_pluginpath(monkeypatch, is_detected):
    mocked_producer = produce_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', mocked_producer)

    monkeypatch.setattr('leapp.libraries.actor.scandnfpluginpath._is_pluginpath_set',
                        lambda path: is_detected)

    scan_dnf_pluginpath()

    assert mocked_producer.called == 1
    assert mocked_producer.model_instances[0].is_pluginpath_detected is is_detected


def test_scan_no_config_file(monkeypatch, tmp_path):
    mocked_producer = produce_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', mocked_producer)

    monkeypatch.setattr('leapp.libraries.actor.scandnfpluginpath.DNF_CONFIG_PATH', str(tmp_path / 'nonexistent.conf'))

    scan_dnf_pluginpath()

    assert mocked_producer.called == 1
    assert mocked_producer.model_instances[0].is_pluginpath_detected is False
