import shutil

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
    ),
    upgrade_bls_dir='/boot/upgrade-loaders/entries',
    upgrade_entry_efi_path='/boot/efi/EFI/leapp'
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


def test_remove_upgrade_efi_entry(monkeypatch):
    run_calls = []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[TEST_EFI_INFO]))

    def mock_run(command, checked=False):
        run_calls.append(command)
        return {'exit_code': 0}

    def rmtree_mocked(tree, *args):
        run_calls.append('shutil.rmtree')
        assert tree == TEST_EFI_INFO.upgrade_bls_dir

    monkeypatch.setattr(removeupgradeefientry, 'run', mock_run)
    monkeypatch.setattr(shutil, 'rmtree', rmtree_mocked)

    removeupgradeefientry.remove_upgrade_efi_entry()

    assert run_calls == [
        ['/bin/mount', '/boot'],
        ['/bin/mount', '/boot/efi'],
        ['/usr/sbin/efibootmgr', '--delete-bootnum', '--bootnum', '0002'],
        ['rm', '-rf', removeupgradeefientry.LEAPP_EFIDIR_CANONICAL_PATH],
        'shutil.rmtree',
        ['/usr/sbin/efibootmgr', '--bootnext', '0001'],
        ['/bin/mount', '-a'],
    ]
