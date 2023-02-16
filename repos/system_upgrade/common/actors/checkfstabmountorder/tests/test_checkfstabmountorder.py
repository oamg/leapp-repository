import pytest

from leapp import reporting
from leapp.libraries.actor.checkfstabmountorder import (
    _get_common_path,
    _get_overshadowing_mount_points,
    check_fstab_mount_order
)
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FstabEntry, MountEntry, StorageInfo

VAR_ENTRY = FstabEntry(fs_spec='', fs_file='/var', fs_vfstype='',
                       fs_mntops='defaults', fs_freq='0', fs_passno='0')
VAR_DUPLICATE_ENTRY = FstabEntry(fs_spec='', fs_file='/var/', fs_vfstype='',
                                 fs_mntops='defaults', fs_freq='0', fs_passno='0')
VAR_LOG_ENTRY = FstabEntry(fs_spec='', fs_file='/var/log', fs_vfstype='',
                           fs_mntops='defaults', fs_freq='0', fs_passno='0')


@pytest.mark.parametrize(
    ('path1', 'path2', 'expected_output'),
    [
        ('', '', ''),
        ('/var', '/var', '/var'),
        ('/var/lib/leapp', '/var/lib', '/var/lib'),
        ('/var/lib/leapp', '/home', '/'),
        ('/var/lib/leapp', '/var/lib/lea', '/var/lib'),
    ]
)
def test_get_common_path(path1, path2, expected_output):
    assert _get_common_path(path1, path2) == expected_output


@pytest.mark.parametrize(
    ('fstab_entries', 'expected_output'),
    [
        (
           ['/var', '/var/log'],
           set()
        ),
        (
           ['/var', '/'],
           {'/var', '/'}
        ),
        (
           ['/var/log', '/var', '/var'],
           {'/var/log', '/var'}
        ),
        (
           ['/var/log', '/home', '/var', '/var/lib/leapp'],
           {'/var/log', '/var'}
        ),
        (
           ['/var/log', '/home', '/var/lib/leapp', '/var'],
           {'/var/log', '/var', '/var/lib/leapp'}
        ),
        (
           ['/var/log', '/home', '/var', '/var/lib/lea', '/var/lib/leapp'],
           {'/var/log', '/var'}
        ),
    ]
)
def test_get_overshadowing_mount_points(fstab_entries, expected_output):
    assert _get_overshadowing_mount_points(fstab_entries) == expected_output


@pytest.mark.parametrize(
    ('storage_info', 'should_inhibit', 'duplicates'),
    [
        (StorageInfo(fstab=[]), False, False),
        (StorageInfo(fstab=[VAR_LOG_ENTRY, VAR_ENTRY]), True, False),
        (StorageInfo(fstab=[VAR_LOG_ENTRY, VAR_ENTRY, VAR_DUPLICATE_ENTRY]), True, True),
        (StorageInfo(fstab=[VAR_ENTRY, VAR_LOG_ENTRY]), False, False),
    ]
)
def test_var_lib_leapp_non_persistent_is_detected(monkeypatch, storage_info, should_inhibit, duplicates):

    created_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[storage_info]))
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    check_fstab_mount_order()

    if should_inhibit:
        assert created_reports.called == 1

        if duplicates:
            assert 'Detected mount points with duplicates:' in created_reports.reports[-1]['summary']
