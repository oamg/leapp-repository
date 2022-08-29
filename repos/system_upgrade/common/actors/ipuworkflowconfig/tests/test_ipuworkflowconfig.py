import json
import os
import tempfile

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import ipuworkflowconfig
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import OSRelease

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


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
        message='A Leapp Command Error occurred.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


def _get_os_release(version='7.9', codename='Maipo'):
    release = OSRelease(
        release_id='rhel',
        name='Red Hat Enterprise Linux Server',
        pretty_name='Red Hat Enterprise Linux',
        version='{} ({})'.format(version, codename),
        version_id='{}'.format(version),
        variant='Server',
        variant_id='server')
    return release


def test_leapp_env_vars(monkeypatch):
    _clean_leapp_envs(monkeypatch)
    monkeypatch.setenv('LEAPP_WHATEVER', '0')
    monkeypatch.setenv('LEAPP_VERBOSE', '1')
    monkeypatch.setenv('LEAPP_DEBUG', '1')
    monkeypatch.setenv('LEAPP_CURRENT_PHASE', 'test')
    monkeypatch.setenv('LEAPP_CURRENT_ACTOR', 'test')
    monkeypatch.setenv('TEST', 'test')
    monkeypatch.setenv('TEST2', 'test')

    assert len(ipuworkflowconfig.get_env_vars()) == 1


def test_get_os_release_info(monkeypatch):
    expected = _get_os_release('7.6')
    assert expected == ipuworkflowconfig.get_os_release(os.path.join(CUR_DIR, 'files/os-release'))

    with pytest.raises(StopActorExecutionError):
        ipuworkflowconfig.get_os_release(os.path.join(CUR_DIR, 'files/non-existent-file'))


def test_get_booted_kernel(monkeypatch):
    monkeypatch.setattr(ipuworkflowconfig, 'run', lambda x: {'stdout': '4.14.0-100.8.2.el7a.x86_64\n'})
    assert ipuworkflowconfig.get_booted_kernel() == '4.14.0-100.8.2.el7a.x86_64'

    monkeypatch.setattr(ipuworkflowconfig, 'run', _raise_call_error)
    with pytest.raises(StopActorExecutionError):
        ipuworkflowconfig.get_booted_kernel()
