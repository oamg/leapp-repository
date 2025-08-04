import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import scan_default_initramfs
from leapp.libraries.common import testutils
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import DefaultInitramfsInfo, DefaultSourceBootEntry


def test_scan_default_initramfs(monkeypatch):
    lsinitrd_output = [
        'Image: /boot/initramfs-5.14.0-570.12.1.el9_6.x86_64.img: 38M',
        '========================================================================',
        'Early CPIO image',
        '========================================================================',
        'drwxr-xr-x   3 root     root            0 Mar 11 04:02 .',
        '-rw-r--r--   1 root     root            2 Mar 11 04:02 early_cpio',
        'drwxr-xr-x   3 root     root            0 Mar 11 04:02 kernel',
        'drwxr-xr-x   3 root     root            0 Mar 11 04:02 kernel/x86',
        'drwxr-xr-x   2 root     root            0 Mar 11 04:02 kernel/x86/microcode',
        '-rw-r--r--   1 root     root       220160 Mar 11 04:02 kernel/x86/microcode/GenuineIntel.bin',
        '========================================================================',
        'Version: dracut-057-87.git20250311.el9_6',
        '',
        'dracut modules:',
        'bash',
        'systemd',
        '========================================',
    ]

    def run_mock(command, split=False):
        if command == ['lsinitrd', '-m', '/boot/initramfs-upgrade.x86_64.img']:
            return {'stdout': lsinitrd_output}
        assert False, f'Unexpected command: {command}'

    default_source_entry_msg = DefaultSourceBootEntry(
        kernel_path='/boot/vmlinuz-upgrade.x86_64',
        initramfs_path='/boot/initramfs-upgrade.x86_64.img'
    )

    actor_mock = testutils.CurrentActorMocked(msgs=[default_source_entry_msg])
    produce_mock = testutils.produce_mocked()

    monkeypatch.setattr(scan_default_initramfs.api, 'current_actor', actor_mock)
    monkeypatch.setattr(scan_default_initramfs.api, 'produce', produce_mock)
    monkeypatch.setattr(scan_default_initramfs, 'run', run_mock)

    scan_default_initramfs.scan_default_initramfs()

    assert produce_mock.called
    assert len(produce_mock.model_instances) == 1
    assert isinstance(produce_mock.model_instances[0], DefaultInitramfsInfo)

    initramfs_info = produce_mock.model_instances[0]
    assert initramfs_info.used_dracut_modules == ['bash', 'systemd']


def test_no_default_boot_entry(monkeypatch):
    monkeypatch.setattr(scan_default_initramfs.api, 'current_actor', testutils.CurrentActorMocked(msgs=[]))

    with pytest.raises(StopActorExecutionError):
        scan_default_initramfs.scan_default_initramfs()


def test_lsinitrd_error(monkeypatch):
    default_boot_entry = DefaultSourceBootEntry(
        kernel_path='/boot/vmlinuz-upgrade.x86_64',
        initramfs_path='/boot/initramfs-upgrade.x86_64.img'
    )

    def run_mock(command, split=False):
        if command == ['lsinitrd', '-m', '/boot/initramfs-upgrade.x86_64.img']:
            raise CalledProcessError('Simulated lsinitrd call error (in tests)', command, 1)
        assert False, f'Unexpected command: {command}'

    actor_mock = testutils.CurrentActorMocked(msgs=[default_boot_entry])
    monkeypatch.setattr(scan_default_initramfs.api, 'current_actor', actor_mock)
    monkeypatch.setattr(scan_default_initramfs.api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(scan_default_initramfs, 'run', run_mock)

    with pytest.raises(StopActorExecutionError):
        scan_default_initramfs.scan_default_initramfs()
