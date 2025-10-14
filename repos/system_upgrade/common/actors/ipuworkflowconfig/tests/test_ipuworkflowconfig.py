import os

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


TEST_UPGRADE_PATHS = {
    'rhel': {
        'default': {
            '8.10': ['9.4', '9.6', '9.7'],
            '8.4': ['9.2'],
            '9.6': ['10.0'],
            '9.7': ['10.1'],
            '8': ['9.4', '9.6'],
            '9': ['10.1'],
        },
        'saphana': {
            '8.10': ['9.6', '9.4'],
            '8': ['9.6', '9.4'],
            '9.6': ['10.0'],
            '9': ['10.0'],
        },
    },
    'centos': {
        'default': {
            '8': ['9'],
            '9': ['10'],
        },
        '_virtual_versions': {
            '8': '8.10',
            '9': '9.7',
            '10': '10.1',
        },
    },
    'almalinux': {
        'default': {
            '8.10': ['9.0', '9.1', '9.2', '9.3', '9.4', '9.5', '9.6', '9.7'],
            '9.7': ['10.0', '10.1'],
        },
    },
}


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
                IPUSourceToPossibleTargets(source_version='8.6', target_versions=['9']),
            ]
        ),
        (
            '80',
            [
                IPUSourceToPossibleTargets(source_version='80.0', target_versions=['81.0']),
            ]
        ),
        (
            '9',
            [
                IPUSourceToPossibleTargets(source_version='9', target_versions=['10']),
                IPUSourceToPossibleTargets(source_version='9.6', target_versions=['10.0']),
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
        '80.0': ['81.0'],
        '8.6': ['9'],
        '9': ['10'],
    }

    result = ipuworkflowconfig.construct_models_for_paths_matching_source_major(RAW_PATHS, source_major_version)
    result = sorted(result, key=lambda x: x.source_version)
    assert result == sorted(expected_result, key=lambda x: x.source_version)


@pytest.mark.parametrize(
    "src_distro,dst_distro,expected",
    [
        ("centos", "rhel", {"8": ["9.4", "9.6", "9.7"], "9": ["10.1"]}),
        ("almalinux", "rhel", {"8.10": ["9.4", "9.6", "9.7"], "9.7": ["10.1"]}),
        ("rhel", "centos", {"8.10": ["9"], "9.7": ["10"]}),
        ("almalinux", "centos", {"8.10": ["9"], "9.7": ["10"]}),
        (
            "rhel",
            "almalinux",
            {
                "8.10": ["9.0", "9.1", "9.2", "9.3", "9.4", "9.5", "9.6", "9.7"],
                "9.7": ["10.0", "10.1"],
            },
        ),
        (
            "centos",
            "almalinux",
            {
                "8": ["9.0", "9.1", "9.2", "9.3", "9.4", "9.5", "9.6", "9.7"],
                "9": ["10.0", "10.1"],
            },
        ),
    ],
)
def test_make_cross_distro_paths(src_distro, dst_distro, expected):
    res = ipuworkflowconfig.make_cross_distro_paths(
        TEST_UPGRADE_PATHS, src_distro, dst_distro, 'default'
    )
    assert res == expected


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
        (
            'almalinux', 'default',
            {
                '8.10': ['9.0', '9.1', '9.2', '9.3', '9.4', '9.5', '9.6'],
                '9.6': ['10.0']
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
        },
        'almalinux': {
            'default': {
                '8.10': ['9.0', '9.1', '9.2', '9.3', '9.4', '9.5', '9.6'],
                '9.6': ['10.0']
            }
        }
    }

    result = ipuworkflowconfig.extract_upgrade_paths_for_distro_and_flavour(
        defined_upgrade_paths, distro, flavour
    )
    assert result == expected_result


@pytest.mark.parametrize(
    ('construction_params', 'expected_versions'),
    [
        (('centos', '8'), '8.10'),
        (('centos', '9'), '9.7'),
        (('rhel', '8.10'), '8.10'),
        (('rhel', '9.4'), '9.4'),
        (('almalinux', '8.10'), '8.10'),
        (('almalinux', '9.6'), '9.6'),
    ]
)
def test_virtual_version_construction(construction_params, expected_versions):
    result = ipuworkflowconfig.get_virtual_version(TEST_UPGRADE_PATHS, *construction_params)
    assert result == expected_versions
