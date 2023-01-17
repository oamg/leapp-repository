import pytest

from leapp import reporting
from leapp.libraries.actor.checkfstabmountorder import (
    _get_common_path,
    _get_incorrectly_ordered_fstab_entries,
    check_fstab_mount_order
)
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FstabEntry, MountEntry, StorageInfo

VAR_ENTRY = FstabEntry(fs_spec='', fs_file='/var/', fs_vfstype='',
                       fs_mntops='defaults', fs_freq='0', fs_passno='0')
VAR_LOG_ENTRY = FstabEntry(fs_spec='', fs_file='/var/log', fs_vfstype='',
                           fs_mntops='defaults', fs_freq='0', fs_passno='0')
HOME_ENTRY = FstabEntry(fs_spec='', fs_file='/home', fs_vfstype='',
                        fs_mntops='defaults', fs_freq='0', fs_passno='0')
VAR_LIB_LEAPP_ENTRY = FstabEntry(fs_spec='', fs_file='/var/lib/leapp', fs_vfstype='',
                                 fs_mntops='defaults', fs_freq='0', fs_passno='0')
VAR_LIB_LEA_ENTRY = FstabEntry(fs_spec='', fs_file='/var/lib/lea/', fs_vfstype='',
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
           [VAR_ENTRY, VAR_LOG_ENTRY],
           []
        ),
        (
           [VAR_LOG_ENTRY, VAR_ENTRY],
           [(VAR_LOG_ENTRY, VAR_ENTRY)]
        ),
        (
           [VAR_LOG_ENTRY, VAR_ENTRY, VAR_ENTRY],
           [(VAR_LOG_ENTRY, VAR_ENTRY), (VAR_LOG_ENTRY, VAR_ENTRY), (VAR_ENTRY, VAR_ENTRY)]
        ),
        (
           [VAR_LOG_ENTRY, HOME_ENTRY, VAR_ENTRY, VAR_LIB_LEAPP_ENTRY],
           [(VAR_LOG_ENTRY, VAR_ENTRY)]
        ),
        (
           [VAR_LOG_ENTRY, HOME_ENTRY, VAR_LIB_LEAPP_ENTRY, VAR_ENTRY],
           [(VAR_LOG_ENTRY, VAR_ENTRY), (VAR_LIB_LEAPP_ENTRY, VAR_ENTRY)]
        ),
        (
           [VAR_LOG_ENTRY, HOME_ENTRY, VAR_ENTRY, VAR_LIB_LEA_ENTRY, VAR_LIB_LEAPP_ENTRY],
           [(VAR_LOG_ENTRY, VAR_ENTRY)]
        ),
    ]
)
def test_incorrectly_ordered_fstab_entries(fstab_entries, expected_output):
    assert list(_get_incorrectly_ordered_fstab_entries(fstab_entries)) == expected_output


@pytest.mark.parametrize(
    ('storage_info', 'should_inhibit'),
    [
        (
            StorageInfo(fstab=[]),
            False
        ),
        (
            StorageInfo(fstab=[VAR_LOG_ENTRY, VAR_ENTRY]),
            True
        ),
        (
            StorageInfo(fstab=[VAR_LOG_ENTRY, VAR_ENTRY, VAR_ENTRY]),
            True
        ),
        (
            StorageInfo(fstab=[VAR_ENTRY, VAR_LOG_ENTRY]),
            False
        ),
    ]
)
def test_var_lib_leapp_non_persistent_is_detected(monkeypatch, storage_info, should_inhibit):

    created_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[storage_info]))
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    check_fstab_mount_order()

    if should_inhibit:
        assert created_reports.called == 1

        mount_points = [fstab_entry.fs_file for fstab_entry in storage_info.fstab]
        if len(set(mount_points)) != len(mount_points):
            assert 'Detected duplicate mount points:' in created_reports.reports[-1]['summary']
