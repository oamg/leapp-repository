import warnings

import pytest

from leapp.libraries.actor import systemfacts
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


def _run_result(stdout):
    return {'stdout': stdout, 'stderr': '', 'signal': None, 'exit_code': 0, 'pid': 1}


@pytest.fixture(autouse=True)
def stub_grubby_info_all_without_enforcing(monkeypatch):
    """
    Avoid invoking real grubby from get_selinux_status(); default: no enforcing=1 in boot entries.
    """

    def mocked_run(cmd, split=False, **dummy_kwargs):
        assert cmd == ['/usr/sbin/grubby', '--info', 'ALL'], f"Unexpected grubby cmd: {cmd}"
        return _run_result('index=0\nkernel="/boot/vmlinuz-1"\nargs="ro rhgb quiet"\nroot="UUID=xxx"\n')

    monkeypatch.setattr(systemfacts, 'run', mocked_run)


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
                     'static_mode': 'enforcing',
                     'enforcing_via_any_cmdline': False}
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
                     'static_mode': 'permissive',
                     'enforcing_via_any_cmdline': False}
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
                     'static_mode': 'permissive',
                     'enforcing_via_any_cmdline': False}
    assert SELinuxFacts(**expected_data) == get_selinux_status()


class MockNoConfigFileOSError:
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
                     'static_mode': 'disabled',
                     'enforcing_via_any_cmdline': False}

    assert SELinuxFacts(**expected_data) == get_selinux_status()


@pytest.mark.skipif(no_selinux, reason=reason_to_skip_msg)
@pytest.mark.parametrize('grubby_stdout,expected', [
    ('index=0\nargs="ro enforcing=1"\n', True),
    ('index=0\nargs="ro enforcing=1 rhgb quiet"\n', True),
    ('index=0\nargs="enforcing=1"\n', True),
    ('index=0\nargs="ro enforcing=1"\nindex=1\nargs="ro rhgb quiet"\n', True),
    ('index=0\nargs="ro rhgb quiet"\nindex=1\nargs="ro enforcing=1"\n', True),
    ('index=0\nargs="ro enforcing=0"\n', False),
    ('index=0\nargs="ro rhgb quiet"\n', False),
    ('index=0\nargs="ro fooenforcing=1"\n', False),
    ('index=0\nargs="ro enforcing=1bar"\n', False),
    ('index=0\nargs="ro"\n', False),
    ('index=0\nargs=""\n', False),
])
def test_bootloader_enforcing_one_detected(monkeypatch, grubby_stdout, expected):
    monkeypatch.setattr(selinux, 'is_selinux_mls_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'security_getenforce', lambda: 1)
    monkeypatch.setattr(selinux, 'selinux_getenforcemode', lambda: [0, 1])
    monkeypatch.setattr(selinux, 'is_selinux_enabled', lambda: 1)
    monkeypatch.setattr(selinux, 'selinux_getpolicytype', lambda: [0, 'targeted'])

    def mocked_run(cmd, split=False, **dummy_kwargs):
        assert cmd == ['/usr/sbin/grubby', '--info', 'ALL'], f"Unexpected grubby cmd: {cmd}"
        return _run_result(grubby_stdout)

    monkeypatch.setattr(systemfacts, 'run', mocked_run)

    fact = get_selinux_status()
    assert fact.enforcing_via_any_cmdline is expected
