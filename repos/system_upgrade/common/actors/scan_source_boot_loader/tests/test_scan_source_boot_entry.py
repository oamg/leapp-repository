import os

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import scan_source_boot_entry
from leapp.libraries.common import testutils
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import DefaultSourceBootEntry


def test_scan_default_source_boot_entry(monkeypatch):
    grubby_default_kernel_output = '/boot/vmlinuz-upgrade.x86_64\n'
    grubby_default_kernel_info_lines = [
        'index=3',
        'kernel="/boot/vmlinuz-upgrade.x86_64"',
        'args="ro console=tty0 console=ttyS0,115200 rd_NO_PLYMOUTH"',
        'root="/dev/mapper/rhel_ibm--p8--kvm--03--guest--02-root"',
        'initrd="/boot/initramfs-upgrade.x86_64.img $tuned_initrd"',
        'title="RHEL-Upgrade-Initramfs"',
        'id="f6f57ac447784f60ba924dfbd5776a1b-upgrade.x86_64"',
    ]

    def run_mock(command, split=False):
        if command == ['grubby', '--default-kernel']:
            return {'stdout': grubby_default_kernel_output}
        if command == ['grubby', '--info', grubby_default_kernel_output.strip()]:
            return {'stdout': grubby_default_kernel_info_lines}
        assert False, f'Unexpected command: {command}'

    def exists_mock(path):
        if path == '/boot/initramfs-upgrade.x86_64.img':
            return True
        return os.path.exists(path)

    produce_mock = testutils.produce_mocked()
    monkeypatch.setattr(scan_source_boot_entry, 'run', run_mock)
    monkeypatch.setattr(scan_source_boot_entry.api, 'produce', produce_mock)
    monkeypatch.setattr(scan_source_boot_entry.os.path, 'exists', exists_mock)

    scan_source_boot_entry.scan_default_source_boot_entry()

    assert produce_mock.called
    assert len(produce_mock.model_instances) == 1
    assert isinstance(produce_mock.model_instances[0], DefaultSourceBootEntry)

    boot_entry_info = produce_mock.model_instances[0]
    assert boot_entry_info.initramfs_path == '/boot/initramfs-upgrade.x86_64.img'
    assert boot_entry_info.kernel_path == '/boot/vmlinuz-upgrade.x86_64'


def test_error_during_grubby_call(monkeypatch):
    def run_mock(command, split=False):
        if command == ['grubby', '--default-kernel']:
            raise CalledProcessError('Simulated grubby call error (in tests)', command, 1)
        assert False, f'Unexpected command: {command}'

    monkeypatch.setattr(scan_source_boot_entry, 'run', run_mock)

    with pytest.raises(StopActorExecutionError):
        scan_source_boot_entry.scan_default_source_boot_entry()
