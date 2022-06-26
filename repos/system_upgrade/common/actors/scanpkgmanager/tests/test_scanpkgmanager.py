import os

import pytest

from leapp.libraries import stdlib
from leapp.libraries.actor import pluginscanner, scanpkgmanager
from leapp.libraries.common import testutils
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PROXY_ADDRESS = 'https://192.168.121.123:3128'
YUM_CONFIG_PATH = '/etc/yum.conf'
DNF_CONFIG_PATH = '/etc/dnf/dnf.conf'


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
    monkeypatch.setattr(scanpkgmanager, '_get_proxy_if_set', lambda x: None)
    monkeypatch.setattr(pluginscanner, 'scan_enabled_package_manager_plugins', lambda: [])

    scanpkgmanager.process()

    assert scanpkgmanager.api.produce.called
    if etcrelease_exists:
        assert api.produce.model_instances[0].etc_releasever
    else:
        assert not api.produce.model_instances[0].etc_releasever


@pytest.mark.parametrize('proxy_set', [True, False])
def test_get_proxy_if_set(monkeypatch, proxy_set):

    config_path = '/path/to/config.conf'
    config_contents = '[main]\n'
    if proxy_set:
        config_contents += 'proxy = \t{} '.format(PROXY_ADDRESS)

    def mocked_get_config_contents(path):
        assert path == config_path
        return config_contents

    monkeypatch.setattr(scanpkgmanager, '_get_config_contents', mocked_get_config_contents)

    proxy = scanpkgmanager._get_proxy_if_set(config_path)

    if proxy_set:
        assert proxy == PROXY_ADDRESS

    assert proxy_set == bool(proxy)


@pytest.mark.parametrize(
    ('proxy_set_in_dnf_config', 'proxy_set_in_yum_config', 'expected_output'),
    [
      (True, True, [PROXY_ADDRESS]),
      (True, False, [PROXY_ADDRESS]),
      (False, False, [])
    ]
)
def test_get_configured_proxies(monkeypatch, proxy_set_in_dnf_config, proxy_set_in_yum_config, expected_output):

    def mocked_get_proxy_if_set(path):
        proxy = PROXY_ADDRESS if proxy_set_in_yum_config else None
        if path == DNF_CONFIG_PATH:
            proxy = PROXY_ADDRESS if proxy_set_in_dnf_config else None
        return proxy

    monkeypatch.setattr(scanpkgmanager, '_get_proxy_if_set', mocked_get_proxy_if_set)

    configured_proxies = scanpkgmanager.get_configured_proxies()
    assert configured_proxies == expected_output
