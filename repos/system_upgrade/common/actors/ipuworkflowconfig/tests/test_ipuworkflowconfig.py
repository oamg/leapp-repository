import json
import os
import tempfile

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import ipuworkflowconfig
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import IPUSourceToPossibleTargets, OSRelease

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


@pytest.mark.parametrize(
    ('source_major_version', 'expected_result'),
    (
        ('7', []),
        (
            '8',
            [
                IPUSourceToPossibleTargets(source_version='8.10', target_versions=['9.4', '9.5', '9.6']),
                IPUSourceToPossibleTargets(source_version='8.4', target_versions=['9.2']),
                IPUSourceToPossibleTargets(source_version='8', target_versions=['9.4', '9.5', '9.6']),
            ]
        ),
        (
            '80',
            [
                IPUSourceToPossibleTargets(source_version='80.0', target_versions=['81.0']),
            ]
        ),
    )
)
def test_construct_models_for_paths_matching_source_major(source_major_version, expected_result):
    RAW_PATHS = {
        '8.10': ['9.4', '9.5', '9.6'],
        '8.4': ['9.2'],
        '9.6': ['10.0'],
        '8': ['9.4', '9.5', '9.6'],
        '80.0': ['81.0']
    }

    result = ipuworkflowconfig.construct_models_for_paths_matching_source_major(RAW_PATHS, source_major_version)
    result = sorted(result, key=lambda x: x.source_version)
    assert result == sorted(expected_result, key=lambda x: x.source_version)


@pytest.mark.parametrize(
    ('distro', 'flavour', 'expected_result'),
    (
        ('fedora', 'default', {}),
        (
            'rhel', 'default',
            {
                '8.10': ['9.4', '9.5', '9.6'],
                '8.4': ['9.2'],
                '9.6': ['10.0'],
                '8': ['9.4', '9.5', '9.6'],
                '9': ['10.0']
            }
        ),
        (
            'rhel', 'saphana',
            {
                '8.10': ['9.6', '9.4'],
                '8': ['9.6', '9.4'],
                '9.6': ['10.0'],
                '9': ['10.0']
            }
        ),
    )
)
def test_load_raw_upgrade_paths_for_distro_and_flavour(monkeypatch, distro, flavour, expected_result):
    defined_upgrade_paths = {
        'rhel': {
            'default': {
                '8.10': ['9.4', '9.5', '9.6'],
                '8.4': ['9.2'],
                '9.6': ['10.0'],
                '8': ['9.4', '9.5', '9.6'],
                '9': ['10.0']
            },
            'saphana': {
                '8.10': ['9.6', '9.4'],
                '8': ['9.6', '9.4'],
                '9.6': ['10.0'],
                '9': ['10.0']
            }
        }
    }
    monkeypatch.setattr(ipuworkflowconfig, 'load_upgrade_paths_definitions', lambda *args: defined_upgrade_paths)

    result = ipuworkflowconfig.load_raw_upgrade_paths_for_distro_and_flavour(distro, flavour)
    assert result == expected_result
