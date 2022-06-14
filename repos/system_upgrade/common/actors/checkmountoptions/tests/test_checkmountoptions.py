from collections import namedtuple
from functools import partial

import pytest

from leapp import reporting
from leapp.libraries.actor.checkmountoptions import check_mount_options
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FstabEntry, MountEntry, StorageInfo


@pytest.mark.parametrize(
    ('fstab_entries', 'mounts', 'should_inhibit'),
    [
        (
            (('/var', 'default'), ),
            (('/var', 'default'), ),
            False
        ),
        (
            (('/var', 'default'), ('/var/lib', 'default'), ),
            (('/var', 'default'), ('/var/lib', 'default'), ),
            False
        ),
        (
            (('/var', 'default'), ('/var/lib/leapp', 'noexec')),
            (('/var', 'default'), ('/var/lib/leapp', 'noexec')),
            True
        ),
        (
            (('/var', 'defaults'), ('/var/lib', 'noexec')),
            (('/var', 'noexec'), ('/var/lib', 'noexec')),
            True
        ),
        (
            (('/var', 'noexec'), ('/var/lib', 'defaults')),
            (('/var', 'noexec'), ('/var/lib', 'noexec')),
            True
        ),
    ]
)
def test_var_mounted_with_noexec_is_detected(monkeypatch, fstab_entries, mounts, should_inhibit):
    mounts = [
        MountEntry(name='/dev/sdaX', tp='ext4', mount=mountpoint, options=options) for mountpoint, options in mounts
    ]

    fstab_entries = [
        FstabEntry(fs_spec='', fs_file=mountpoint, fs_vfstype='',
                   fs_mntops=opts, fs_freq='0', fs_passno='0') for mountpoint, opts in fstab_entries
    ]

    storage_info = StorageInfo(mount=mounts, fstab=fstab_entries)

    created_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[storage_info]))
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    check_mount_options()

    assert bool(created_reports.called) == should_inhibit
