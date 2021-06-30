import warnings

import pytest

from leapp.libraries.actor.systemfacts import get_selinux_status
from leapp.models import SELinuxFacts

no_selinux = False
try:
    import selinux
except ImportError:
    no_selinux = True
    warnings.warn(
        'Tests which uses `selinux` will be skipped'
        ' due to library unavailability.', ImportWarning)


reason_to_skip_msg = "Selinux is not available"

# FIXME: create valid tests...


@pytest.mark.skipif(no_selinux, reason=reason_to_skip_msg)
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


@pytest.mark.skipif(no_selinux, reason=reason_to_skip_msg)
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


@pytest.mark.skipif(no_selinux, reason=reason_to_skip_msg)
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


@pytest.mark.skipif(no_selinux, reason=reason_to_skip_msg)
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
