import pytest

from leapp import reporting
from leapp.libraries.actor.checkpersistentmounts import check_persistent_mounts
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FstabEntry, MountEntry, StorageInfo

MOUNT_ENTRY = MountEntry(name='/dev/sdaX', tp='ext4', mount='/var/lib/leapp', options='defaults')

FSTAB_ENTRY = FstabEntry(fs_spec='', fs_file='/var/lib/leapp', fs_vfstype='',
                         fs_mntops='defaults', fs_freq='0', fs_passno='0')


@pytest.mark.parametrize(
    ('storage_info', 'should_inhibit'),
    [
        (
            StorageInfo(mount=[MOUNT_ENTRY], fstab=[]),
            True
        ),
        (
            StorageInfo(mount=[], fstab=[FSTAB_ENTRY]),
            False
        ),
        (
            StorageInfo(mount=[MOUNT_ENTRY], fstab=[FSTAB_ENTRY]),
            False
        ),
    ]
)
def test_var_lib_leapp_non_persistent_is_detected(monkeypatch, storage_info, should_inhibit):

    created_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[storage_info]))
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    check_persistent_mounts()

    assert bool(created_reports.called) == should_inhibit
