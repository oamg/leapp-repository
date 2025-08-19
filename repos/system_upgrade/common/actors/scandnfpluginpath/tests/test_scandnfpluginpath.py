import os

import pytest

from leapp.libraries.actor import scandnfpluginpath
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DnfPluginPathDetected


@pytest.mark.parametrize('is_detected', [False, True])
def test_scan_detects_pluginpath(monkeypatch, is_detected):
    mocked_producer = produce_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', mocked_producer)

    monkeypatch.setattr(scandnfpluginpath, '_is_pluginpath_set',
                        lambda path: is_detected)

    scandnfpluginpath.scan_dnf_pluginpath()

    assert mocked_producer.called == 1
    assert mocked_producer.model_instances[0].is_pluginpath_detected is is_detected


@pytest.mark.parametrize(('config_file', 'result'), [
    ('files/dnf_config_no_pluginpath', False),
    ('files/dnf_config_with_pluginpath', True),
    ('files/dnf_config_incorrect_pluginpath', False),
    ('files/not_existing_file.conf', False)
])
def test_is_pluginpath_set(config_file, result):
    CUR_DIR = os.path.dirname(os.path.abspath(__file__))

    assert scandnfpluginpath._is_pluginpath_set(os.path.join(CUR_DIR, config_file)) == result


def test_scan_no_config_file(monkeypatch):
    mocked_producer = produce_mocked()
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', mocked_producer)
    monkeypatch.setattr(api, 'current_logger', lambda: logger)

    filename = 'files/not_existing_file.conf'
    monkeypatch.setattr(scandnfpluginpath, 'DNF_CONFIG_PATH', filename)
    scandnfpluginpath.scan_dnf_pluginpath()

    assert mocked_producer.called == 1
    assert mocked_producer.model_instances[0].is_pluginpath_detected is False

    assert 'The %s file is missing.' in logger.warnmsg
    assert filename in logger.warnmsg
