import pytest

from leapp import reporting
from leapp.libraries.actor.checkfstabapifsoverride import check_fstab_api_fs_override
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FstabEntry, StorageInfo


def _fstab(fs_spec, fs_file, fs_vfstype, fs_mntops='defaults'):
    return FstabEntry(
        fs_spec=fs_spec, fs_file=fs_file, fs_vfstype=fs_vfstype,
        fs_mntops=fs_mntops, fs_freq='0', fs_passno='0',
    )


# --- Entries that SHOULD inhibit (invalid API fs overrides) ---
_SHM_LVM = _fstab('/dev/mapper/vg00-shm', '/dev/shm', 'xfs')
_SHM_TMPFS_LABEL = _fstab('LABEL=mydata', '/dev/shm', 'tmpfs')
_SHM_LVM_TRAILING = _fstab('/dev/mapper/vg00-shm', '/dev/shm/', 'xfs')
_PROC_EXT4 = _fstab('/dev/sda5', '/proc', 'ext4')
_SYS_LVM = _fstab('/dev/mapper/vg00-sys', '/sys', 'xfs')
_SYS_LVM_SYSFS = _fstab('/dev/mapper/vg00-sys', '/sys', 'sysfs')
_SYS_UUID = _fstab('UUID=023e51f5-b590-4de5-ab21-cf33ecasasas', '/sys', 'xfs')
_SYS_UUID_SYSFS = _fstab('UUID=023e51f5-b590-4de5-ab21-cf33ecasasas', '/sys', 'sysfs')
_RUN_PARTUUID = _fstab('PARTUUID=abcd-1234', '/run', 'ext4')
_RUN_UUID = _fstab('UUID=aabbccdd-1234-5678-9012-aabbccddeeff', '/run', 'ext4')
_SHM_UUID = _fstab('UUID=12345678-abcd-ef01-2345-6789abcdef01', '/dev/shm', 'xfs')
_PROC_BIND = _fstab('/some/dir', '/proc', 'none', fs_mntops='bind')

# --- Entries that should NOT inhibit ---
_SHM_TMPFS = _fstab('tmpfs', '/dev/shm', 'tmpfs')
_PROC_PROC = _fstab('proc', '/proc', 'proc')
_SYS_SYSFS = _fstab('sysfs', '/sys', 'sysfs')
_PROC_NONE = _fstab('none', '/proc', 'proc')
_RUN_TMPFS = _fstab('tmpfs', '/run', 'tmpfs')
_HOME_EXT4 = _fstab('/dev/mapper/fedora-home', '/home', 'ext4')
_ROOT_XFS = _fstab('/dev/mapper/fedora-root', '/', 'xfs')
_VAR_UUID = _fstab('UUID=aabbccdd-1122-3344-5566-778899aabbcc', '/var', 'xfs')
_OPT_LABEL = _fstab('LABEL=optdata', '/opt', 'ext4')
_DATA_PARTUUID = _fstab('PARTUUID=abcd-5678', '/data', 'xfs')
_BOOT_UUID = _fstab('UUID=01234567-89ab-cdef-0123-456789abcdef', '/boot', 'ext2')
_MNT_LABEL = _fstab('LABEL=backup', '/mnt/backup', 'ext4')
_SRV_LVM = _fstab('/dev/mapper/vg00-srv', '/srv', 'xfs')
_HOME_BIND = _fstab('/exports/home', '/home', 'none', fs_mntops='bind')
_MNT_BIND = _fstab('/data/shared', '/mnt/shared', 'none', fs_mntops='bind')


@pytest.mark.parametrize(
    ('fstab_entries', 'should_inhibit'),
    [
        # Invalid overrides of pseudo-filesystem mountpoints
        ([_SHM_LVM], True),
        ([_PROC_EXT4], True),
        ([_SHM_LVM_TRAILING], True),
        ([_SYS_LVM], True),
        ([_SYS_LVM_SYSFS], True),
        ([_SYS_UUID], True),
        ([_SYS_UUID_SYSFS], True),
        ([_SHM_TMPFS_LABEL], True),
        ([_RUN_PARTUUID], True),
        ([_RUN_UUID], True),
        ([_SHM_UUID], True),
        ([_PROC_BIND], True),
        # Valid pseudo-filesystem entries
        ([_SHM_TMPFS, _PROC_PROC, _SYS_SYSFS], False),
        ([_PROC_NONE], False),
        ([_RUN_TMPFS], False),
        # Normal mounts (not pseudo-fs paths) with various source types
        ([_HOME_EXT4, _ROOT_XFS], False),
        ([_VAR_UUID], False),
        ([_OPT_LABEL], False),
        ([_DATA_PARTUUID], False),
        ([_BOOT_UUID], False),
        ([_MNT_LABEL], False),
        ([_SRV_LVM], False),
        # Bind mounts on normal paths
        ([_HOME_BIND], False),
        ([_MNT_BIND], False),
        # Mixed valid entries
        ([_HOME_EXT4, _VAR_UUID, _BOOT_UUID, _SHM_TMPFS], False),
        # Empty fstab
        ([], False),
    ],
)
def test_check_fstab_api_fs_override(monkeypatch, fstab_entries, should_inhibit):
    created_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[StorageInfo(fstab=fstab_entries)]
    ))
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    check_fstab_api_fs_override()

    assert bool(created_reports.called) == should_inhibit


def test_report_lists_only_problematic_entries(monkeypatch):
    created_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[StorageInfo(fstab=[_SHM_LVM, _PROC_EXT4, _HOME_EXT4])]
    ))
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    check_fstab_api_fs_override()

    assert created_reports.called == 1
    summary = created_reports.reports[0]['summary']
    assert '/dev/shm' in summary
    assert '/proc' in summary
    assert '/home' not in summary


def test_no_storage_info(monkeypatch):
    created_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    check_fstab_api_fs_override()

    assert not created_reports.called
