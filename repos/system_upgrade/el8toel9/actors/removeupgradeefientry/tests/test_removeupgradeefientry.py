import os

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import removeupgradeefientry
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import ArmWorkaroundEFIBootloaderInfo, EFIBootEntry

TEST_EFI_INFO = ArmWorkaroundEFIBootloaderInfo(
    original_entry=EFIBootEntry(
        boot_number='0001',
        label='Redhat',
        active=True,
        efi_bin_source="HD(.*)/File(\\EFI\\redhat\\shimx64.efi)",
    ),
    upgrade_entry=EFIBootEntry(
        boot_number='0002',
        label='Leapp',
        active=True,
        efi_bin_source="HD(.*)/File(\\EFI\\leapp\\shimx64.efi)",
    )
)


def test_get_workaround_efi_info_single_entry(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[TEST_EFI_INFO]))

    result = removeupgradeefientry.get_workaround_efi_info()
    assert result == TEST_EFI_INFO


def test_get_workaround_efi_info_multiple_entries(monkeypatch):
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[TEST_EFI_INFO, TEST_EFI_INFO]))
    monkeypatch.setattr(api, 'current_logger', logger)

    result = removeupgradeefientry.get_workaround_efi_info()
    assert result == TEST_EFI_INFO
    assert 'Unexpectedly received more than one UpgradeEFIBootEntry message.' in logger.warnmsg


def test_get_workaround_efi_info_no_entry(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))

    with pytest.raises(StopActorExecutionError, match='Could not remove UEFI boot entry for the upgrade initramfs'):
        removeupgradeefientry.get_workaround_efi_info()


def test_copy_grub_files(monkeypatch):
    copy_file_calls = []

    def mock_copy_file(src, dst):
        copy_file_calls.append((src, dst))

    monkeypatch.setattr(removeupgradeefientry, '_copy_file', mock_copy_file)
    monkeypatch.setattr(os.path, 'exists', lambda path: True)

    removeupgradeefientry._copy_grub_files(['required'], ['optional'])

    assert (
        os.path.join(removeupgradeefientry.LEAPP_EFIDIR_CANONICAL_PATH, 'required'),
        os.path.join(removeupgradeefientry.RHEL_EFIDIR_CANONICAL_PATH, 'required'),
    ) in copy_file_calls
    assert (
        os.path.join(removeupgradeefientry.LEAPP_EFIDIR_CANONICAL_PATH, 'optional'),
        os.path.join(removeupgradeefientry.RHEL_EFIDIR_CANONICAL_PATH, 'optional'),
    ) in copy_file_calls


def test_copy_grub_files_missing_required(monkeypatch):
    monkeypatch.setattr(os.path, 'exists', lambda path: False)

    with pytest.raises(StopActorExecutionError, match='Required file required does not exists'):
        removeupgradeefientry._copy_grub_files(['required'], [])


def test_remove_upgrade_efi_entry(monkeypatch):
    run_calls = []
    copy_grub_files_calls = []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[TEST_EFI_INFO]))

    def mock_run(command, checked=False):
        run_calls.append(command)
        return {'exit_code': 0}

    def mock_copy_grub_files(required, optional):
        copy_grub_files_calls.append((required, optional))

    monkeypatch.setattr(removeupgradeefientry, '_copy_grub_files', mock_copy_grub_files)
    monkeypatch.setattr(removeupgradeefientry, '_link_grubenv_to_rhel_entry', lambda: None)
    monkeypatch.setattr(removeupgradeefientry, 'run', mock_run)

    removeupgradeefientry.remove_upgrade_efi_entry()

    assert run_calls == [
        ['/bin/mount', '/boot'],
        ['/bin/mount', '/boot/efi'],
        ['/usr/sbin/efibootmgr', '--delete-bootnum', '--bootnum', '0002'],
        ['rm', '-rf', removeupgradeefientry.LEAPP_EFIDIR_CANONICAL_PATH],
        ['/usr/sbin/efibootmgr', '--bootnext', '0001'],
        ['/bin/mount', '-a'],
    ]
