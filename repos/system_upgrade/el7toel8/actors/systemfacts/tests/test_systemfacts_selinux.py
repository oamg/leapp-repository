import six
import pytest

from leapp.libraries.actor.systemfacts import get_selinux_status
from leapp.models import SELinuxFacts

if six.PY2:
    import selinux


# FIXME: create valid tests...

@pytest.mark.skipif(six.PY3, reason="skipped in python 3 - raise ModuleNotFoundError on selinux")
def test_selinux_enabled_enforcing(monkeypatch):
    """
    Test case SELinux is enabled in enforcing mode
    """
    monkeypatch.setattr(selinux, 'is_selinux_mls_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'security_getenforce', lambda: 1)
    monkeypatch.setattr(selinux, 'selinux_getenforcemode', lambda: [0, 1])
    monkeypatch.setattr(selinux, 'is_selinux_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'selinux_getpolicytype', lambda: [0, 'targeted'])
    expected_data = {'policy': 'targeted',
                     'mls_enabled': True,
                     'enabled': True,
                     'runtime_mode': 'enforcing',
                     'static_mode': 'enforcing'}
    assert SELinuxFacts(**expected_data) == get_selinux_status()


@pytest.mark.skipif(six.PY3, reason="skipped in python 3 - raise ModuleNotFoundError on selinux")
def test_selinux_enabled_permissive(monkeypatch):
    """
    Test case SELinux is enabled in permissive mode
    """
    monkeypatch.setattr(selinux, 'is_selinux_mls_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'security_getenforce', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getenforcemode', lambda: [0, 0])
    monkeypatch.setattr(selinux, 'is_selinux_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'selinux_getpolicytype', lambda: [0, 'targeted'])
    expected_data = {'policy': 'targeted',
                     'mls_enabled': True,
                     'enabled': True,
                     'runtime_mode': 'permissive',
                     'static_mode': 'permissive'}
    assert SELinuxFacts(**expected_data) == get_selinux_status()


@pytest.mark.skipif(six.PY3, reason="skipped in python 3 - raise ModuleNotFoundError on selinux")
def test_selinux_disabled(monkeypatch):
    """
    Test case SELinux is disabled
    """
    monkeypatch.setattr(selinux, 'is_selinux_mls_enabled', lambda: 0)
    monkeypatch.setattr(selinux, 'security_getenforce', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getenforcemode', lambda: [0, 0])
    monkeypatch.setattr(selinux, 'is_selinux_enabled', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getpolicytype', lambda: [0, 'targeted'])
    expected_data = {'policy': 'targeted',
                     'mls_enabled': False,
                     'enabled': False,
                     'runtime_mode': 'permissive',
                     'static_mode': 'permissive'}
    assert SELinuxFacts(**expected_data) == get_selinux_status()


class MockNoConfigFileOSError(object):
    def __init__(self):
        raise OSError


@pytest.mark.skipif(six.PY3, reason="skipped in python 3 - raise ModuleNotFoundError on selinux")
def test_selinux_disabled_no_config_file(monkeypatch):
    """
    Test case SELinux is disabled
    """
    monkeypatch.setattr(selinux, 'is_selinux_mls_enabled', lambda: 0)
    monkeypatch.setattr(selinux, 'security_getenforce', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getenforcemode', MockNoConfigFileOSError)
    monkeypatch.setattr(selinux, 'is_selinux_enabled', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getpolicytype', lambda: [0, 'targeted'])
    expected_data = {'policy': 'targeted',
                     'mls_enabled': False,
                     'enabled': False,
                     'runtime_mode': 'permissive',
                     'static_mode': 'disabled'}

    assert SELinuxFacts(**expected_data) == get_selinux_status()
