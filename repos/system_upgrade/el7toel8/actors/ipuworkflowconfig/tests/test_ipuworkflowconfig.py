import os

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import library
from leapp.libraries.common.testutils import produce_mocked, create_report_mocked
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import OSRelease


def _clean_leapp_envs(monkeypatch):
    """
    Clean all LEAPP environment variables before running the test to have
    fresh env.
    """
    for k, _ in os.environ.items():
        if k.startswith('LEAPP'):
            monkeypatch.delenv(k)


def _raise_call_error(*args):
    raise CalledProcessError(
        message='A Leapp Command Error occured.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


def test_leapp_env_vars(monkeypatch):
    _clean_leapp_envs(monkeypatch)
    monkeypatch.setenv('LEAPP_WHATEVER', '0')
    monkeypatch.setenv('LEAPP_VERBOSE', '1')
    monkeypatch.setenv('LEAPP_DEBUG', '1')
    monkeypatch.setenv('LEAPP_CURRENT_PHASE', 'test')
    monkeypatch.setenv('LEAPP_CURRENT_ACTOR', 'test')
    monkeypatch.setenv('TEST', 'test')
    monkeypatch.setenv('TEST2', 'test')

    assert len(library.get_env_vars()) == 1


def test_get_target_version(monkeypatch):
    monkeypatch.delenv('LEAPP_DEVEL_TARGET_RELEASE', raising=False)
    assert library.get_target_version() == library.CURRENT_TARGET_VERSION
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '')
    assert library.get_target_version() == library.CURRENT_TARGET_VERSION
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '1.2.3')
    assert library.get_target_version() == '1.2.3'
    monkeypatch.delenv('LEAPP_DEVEL_TARGET_RELEASE', raising=True)


def test_get_os_release_info(monkeypatch):
    expected = OSRelease(
        release_id='rhel',
        name='Red Hat Enterprise Linux Server',
        pretty_name='Red Hat Enterprise Linux',
        version='7.6 (Maipo)',
        version_id='7.6',
        variant='Server',
        variant_id='server')
    assert expected == library.get_os_release('tests/files/os-release')

    with pytest.raises(StopActorExecutionError):
        library.get_os_release('tests/files/non-existent-file')


def test_get_booted_kernel(monkeypatch):
    monkeypatch.setattr(library, 'run', lambda x: {'stdout': '4.14.0-100.8.2.el7a.x86_64\n'})
    assert library.get_booted_kernel() == '4.14.0-100.8.2.el7a.x86_64'

    monkeypatch.setattr(library, 'run', _raise_call_error)
    with pytest.raises(StopActorExecutionError):
        library.get_booted_kernel()
