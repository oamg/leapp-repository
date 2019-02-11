import selinux

from leapp.libraries.actor.systemfacts import get_selinux_status
from leapp.models import SELinuxFacts


def test_selinux_enabled_enforcing(monkeypatch):
    """
    Test case SELinux is enabled in enforcing mode
    """
    monkeypatch.setattr(selinux, 'is_selinux_mls_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'security_getenforce', lambda: 1)
    monkeypatch.setattr(selinux, 'selinux_getenforcemode', lambda: 1)
    monkeypatch.setattr(selinux, 'is_selinux_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'selinux_getpolicytype', lambda: ('', 'targeted'))
    expected_data = {'policy': 'targeted',
                     'mls_enabled': True,
                     'enabled': True,
                     'runtime_mode': 'enforcing',
                     'static_mode': 'enforcing'}
    assert SELinuxFacts(**expected_data) == get_selinux_status()


def test_selinux_enabled_permissive(monkeypatch):
    """
    Test case SELinux is enabled in permissive mode
    """
    monkeypatch.setattr(selinux, 'is_selinux_mls_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'security_getenforce', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getenforcemode', lambda: 0)
    monkeypatch.setattr(selinux, 'is_selinux_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'selinux_getpolicytype', lambda: ('', 'targeted'))
    expected_data = {'policy': 'targeted',
                     'mls_enabled': True,
                     'enabled': True,
                     'runtime_mode': 'permissive',
                     'static_mode': 'permissive'}
    assert SELinuxFacts(**expected_data) == get_selinux_status()


def test_selinux_disabled(monkeypatch):
    """
    Test case SELinux is disabled
    """
    monkeypatch.setattr(selinux, 'is_selinux_mls_enabled', lambda: 0)
    monkeypatch.setattr(selinux, 'security_getenforce', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getenforcemode', lambda: 0)
    monkeypatch.setattr(selinux, 'is_selinux_enabled', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getpolicytype', lambda: ('', 'targeted'))
    expected_data = {'policy': 'targeted',
                     'mls_enabled': False,
                     'enabled': False,
                     'runtime_mode': 'permissive',
                     'static_mode': 'permissive'}
    assert SELinuxFacts(**expected_data) == get_selinux_status()


class MockNoConfigFileOSError:
    def __init__(self):
        raise OSError


def test_selinux_disabled_no_config_file(monkeypatch):
    """
    Test case SELinux is disabled
    """
    monkeypatch.setattr(selinux, 'is_selinux_mls_enabled', lambda: 0)
    monkeypatch.setattr(selinux, 'security_getenforce', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getenforcemode', MockNoConfigFileOSError)
    monkeypatch.setattr(selinux, 'is_selinux_enabled', lambda: 0)
    monkeypatch.setattr(selinux, 'selinux_getpolicytype', lambda: ('', 'targeted'))
    expected_data = {'policy': 'targeted',
                     'mls_enabled': False,
                     'enabled': False,
                     'runtime_mode': 'permissive',
                     'static_mode': 'disabled'}

    assert SELinuxFacts(**expected_data) == get_selinux_status()
