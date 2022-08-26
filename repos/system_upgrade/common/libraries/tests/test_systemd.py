import os
from functools import partial

import pytest

from leapp.libraries.common import systemd
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import SystemdServiceFile, SystemdServicePreset

CURR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_get_service_files(monkeypatch):
    def run_mocked(cmd, *args, **kwargs):
        if cmd == ['systemctl', 'list-unit-files'] + systemd._SYSTEMCTL_CMD_OPTIONS:
            return {'stdout': [
                'auditd.service                                enabled',
                'crond.service                                 enabled ',
                'dbus.service                                  static  ',
                'dnf-makecache.service                         static  ',
                'firewalld.service                             enabled ',
                'getty@.service                                enabled ',
                'gssproxy.service                              disabled',
                'kdump.service                                 enabled ',
                'mdmon@.service                                static  ',
                'nfs.service                                   disabled',
                'polkit.service                                static  ',
                'rescue.service                                static  ',
                'rngd.service                                  enabled ',
                'rsyncd.service                                disabled',
                'rsyncd@.service                               static  ',
                'smartd.service                                enabled ',
                'sshd.service                                  enabled ',
                'sshd@.service                                 static  ',
                'wpa_supplicant.service                        disabled'
            ]}
        raise ValueError('Attempted to call unexpected command: {}'.format(cmd))

    monkeypatch.setattr(systemd, 'run', run_mocked)
    service_files = systemd.get_service_files()

    expected = [
        SystemdServiceFile(name='auditd.service', state='enabled'),
        SystemdServiceFile(name='crond.service', state='enabled'),
        SystemdServiceFile(name='dbus.service', state='static'),
        SystemdServiceFile(name='dnf-makecache.service', state='static'),
        SystemdServiceFile(name='firewalld.service', state='enabled'),
        SystemdServiceFile(name='getty@.service', state='enabled'),
        SystemdServiceFile(name='gssproxy.service', state='disabled'),
        SystemdServiceFile(name='kdump.service', state='enabled'),
        SystemdServiceFile(name='mdmon@.service', state='static'),
        SystemdServiceFile(name='nfs.service', state='disabled'),
        SystemdServiceFile(name='polkit.service', state='static'),
        SystemdServiceFile(name='rescue.service', state='static'),
        SystemdServiceFile(name='rngd.service', state='enabled'),
        SystemdServiceFile(name='rsyncd.service', state='disabled'),
        SystemdServiceFile(name='rsyncd@.service', state='static'),
        SystemdServiceFile(name='smartd.service', state='enabled'),
        SystemdServiceFile(name='sshd.service', state='enabled'),
        SystemdServiceFile(name='sshd@.service', state='static'),
        SystemdServiceFile(name='wpa_supplicant.service', state='disabled')
    ]

    assert service_files == expected


def test_preset_files_overrides():
    etc_files = [
        '/etc/systemd/system-preset/00-abc.preset',
        '/etc/systemd/system-preset/preset_without_prio.preset'
    ]
    usr_files = [
        '/usr/lib/systemd/system-preset/00-abc.preset',
        '/usr/lib/systemd/system-preset/99-xyz.preset',
        '/usr/lib/systemd/system-preset/preset_without_prio.preset'
    ]

    expected = [
        '/usr/lib/systemd/system-preset/99-xyz.preset',
        '/etc/systemd/system-preset/00-abc.preset',
        '/etc/systemd/system-preset/preset_without_prio.preset'
    ]

    presets = systemd._join_presets_resolving_overrides(etc_files, usr_files)
    assert sorted(presets) == sorted(expected)


def test_preset_files_block_override(monkeypatch):
    etc_files = [
        '/etc/systemd/system-preset/00-abc.preset'
    ]
    usr_files = [
        '/usr/lib/systemd/system-preset/00-abc.preset',
        '/usr/lib/systemd/system-preset/99-xyz.preset'
    ]

    expected = [
        '/usr/lib/systemd/system-preset/99-xyz.preset',
    ]

    def islink_mocked(path):
        return path == '/etc/systemd/system-preset/00-abc.preset'

    def readlink_mocked(path):
        if path == '/etc/systemd/system-preset/00-abc.preset':
            return '/dev/null'
        raise OSError

    monkeypatch.setattr(os.path, 'islink', islink_mocked)
    monkeypatch.setattr(os, 'readlink', readlink_mocked)

    presets = systemd._join_presets_resolving_overrides(etc_files, usr_files)
    assert sorted(presets) == sorted(expected)


TEST_SYSTEMD_LOAD_PATH = [os.path.join(CURR_DIR, 'test_systemd_files/')]

TESTING_PRESET_FILES = [
    os.path.join(CURR_DIR, '00-test.preset'),
    os.path.join(CURR_DIR, '01-test.preset')
]

TESTING_PRESET_WITH_INVALID_ENTRIES = os.path.join(CURR_DIR, '05-invalid.preset')

_PARSE_PRESET_ENTRIES_TEST_DEFINITION = (
    ('enable example.service', {'example.service': 'enable'}),
    ('disable abc.service', {'abc.service': 'disable'}),
    ('enable template@.service', {'template@.service': 'enable'}),
    ('disable template2@.service', {'template2@.service': 'disable'}),
    ('disable template@.service instance1 instance2', {
        'template@instance1.service': 'disable',
        'template@instance2.service': 'disable'
    }),
    ('enable globbed*.service', {'globbed-one.service': 'enable', 'globbed-two.service': 'enable'}),
    ('enable example.*', {'example.service': 'enable', 'example.socket': 'enable'}),
    ('disable *', {
            'example.service': 'disable',
            'abc.service': 'disable',
            'template@.service': 'disable',
            'template2@.service': 'disable',
            'globbed-one.service': 'disable',
            'globbed-two.service': 'disable',
            'example.socket': 'disable',
            'extra.service': 'disable'
    })
)


@pytest.mark.parametrize('entry,expected', _PARSE_PRESET_ENTRIES_TEST_DEFINITION)
def test_parse_preset_entry(monkeypatch, entry, expected):
    presets = {}
    systemd._parse_preset_entry(entry, presets, TEST_SYSTEMD_LOAD_PATH)
    assert presets == expected


@pytest.mark.parametrize(
    'entry',
    [
        ('hello.service'),
        ('mask hello.service'),
        ('enable'),
    ]
)
def test_parse_preset_entry_invalid(monkeypatch, entry):
    presets = {}
    with pytest.raises(ValueError, match=r'^Invalid preset file entry: '):
        systemd._parse_preset_entry(entry, presets, TEST_SYSTEMD_LOAD_PATH)


def test_parse_preset_files(monkeypatch):

    expected = {
        'example.service': 'enable',
        'example.socket': 'disable',
        'abc.service': 'disable',
        'template@.service': 'disable',
        'template@instance1.service': 'enable',
        'template@instance2.service': 'enable',
        'globbed-one.service': 'enable',
        'globbed-two.service': 'enable',
        'extra.service': 'disable',
        'template2@.service': 'disable'
    }

    presets = systemd._parse_preset_files(TESTING_PRESET_FILES, TEST_SYSTEMD_LOAD_PATH, False)
    assert presets == expected


def test_parse_preset_files_invalid():
    with pytest.raises(ValueError):
        systemd._parse_preset_files(
            [TESTING_PRESET_WITH_INVALID_ENTRIES], TEST_SYSTEMD_LOAD_PATH, ignore_invalid_entries=False
        )


def test_parse_preset_files_ignore_invalid(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    invalid_preset_files = [TESTING_PRESET_WITH_INVALID_ENTRIES]
    presets = systemd._parse_preset_files(
        invalid_preset_files, TEST_SYSTEMD_LOAD_PATH, ignore_invalid_entries=True
    )

    for entry in ('enable', 'hello.service', 'mask hello.service'):
        msg = 'Invalid preset file {}: Invalid preset file entry: "{}"'.format(invalid_preset_files[0], entry)
        assert msg in api.current_logger.warnmsg

    assert presets == {'example.service': 'disable'}


def parse_preset_files_mocked():
    mocked = partial(systemd._parse_preset_files, load_path=TEST_SYSTEMD_LOAD_PATH)

    def impl(preset_files, load_path, ignore_invalid_entries):
        return mocked(preset_files, ignore_invalid_entries=ignore_invalid_entries)
    return impl


def test_get_service_preset_files(monkeypatch):

    def get_system_preset_files_mocked():
        return TESTING_PRESET_FILES

    monkeypatch.setattr(systemd, '_get_system_preset_files', get_system_preset_files_mocked)
    monkeypatch.setattr(systemd, '_parse_preset_files', parse_preset_files_mocked())

    service_files = [
        SystemdServiceFile(name='abc.service', state='transient'),
        SystemdServiceFile(name='example.service', state='static'),
        SystemdServiceFile(name='example.socket', state='masked'),
        SystemdServiceFile(name='extra.service', state='disabled'),
        SystemdServiceFile(name='template2@.service', state='enabled'),
        SystemdServiceFile(name='template@.service', state='enabled'),
    ]

    expected = [
        # dont expect example.service since it's static
        # dont expect abc.service since it's transient
        SystemdServicePreset(service='template@.service', state='disable'),
        SystemdServicePreset(service='template@instance1.service', state='enable'),
        SystemdServicePreset(service='template@instance2.service', state='enable'),
        SystemdServicePreset(service='globbed-one.service', state='enable'),
        SystemdServicePreset(service='globbed-two.service', state='enable'),
        SystemdServicePreset(service='extra.service', state='disable'),
        SystemdServicePreset(service='template2@.service', state='disable')
    ]

    presets = systemd.get_system_service_preset_files(service_files, False)
    assert sorted(presets, key=lambda e: e.service) == sorted(expected, key=lambda e: e.service)


def test_get_service_preset_files_invalid(monkeypatch):

    def get_system_preset_files_mocked():
        return [TESTING_PRESET_WITH_INVALID_ENTRIES]

    monkeypatch.setattr(systemd, '_get_system_preset_files', get_system_preset_files_mocked)
    monkeypatch.setattr(systemd, '_parse_preset_files', parse_preset_files_mocked())

    with pytest.raises(ValueError):
        # doesn't matter what service_files are
        systemd.get_system_service_preset_files([], ignore_invalid_entries=False)
