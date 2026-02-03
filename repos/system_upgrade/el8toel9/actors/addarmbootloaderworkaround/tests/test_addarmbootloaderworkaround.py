import os
from unittest import mock

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import addupgradebootloader
from leapp.libraries.common import efi
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, make_OSError, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import ArmWorkaroundEFIBootloaderInfo, EFIBootEntry, TargetUserSpaceInfo

TEST_RHEL_EFI_ENTRY = efi.EFIBootLoaderEntry(
            '0000',
            'Red Hat Enterprise Linux',
            True,
            'File(\\EFI\\redhat\\shimaa64.efi)'
        )
TEST_UPGRADE_EFI_ENTRY = efi.EFIBootLoaderEntry(
            '0001',
            addupgradebootloader.UPGRADE_EFI_ENTRY_LABEL,
            True,
            'File(\\EFI\\leapp\\shimaa64.efi)'
        )


class MockEFIBootInfo:
    def __init__(self, entries):
        assert len(entries) > 0

        self.boot_order = tuple(entry.boot_number for entry in entries)
        self.current_bootnum = self.boot_order[0]
        self.next_bootnum = None
        self.entries = {
            entry.boot_number: entry for entry in entries
        }


class IsolatedActionsMocked:
    def __init__(self):
        self.copytree_from_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def copytree_from(self, src, dst):
        self.copytree_from_calls.append((src, dst))


@pytest.mark.parametrize('dst_exists', [True, False])
def test_copy_file(monkeypatch, dst_exists):
    src_path = '/src/file.txt'
    dst_path = '/dst/file.txt'
    logger = logger_mocked()

    copy2_calls = []

    def mock_copy2(src, dst):
        copy2_calls.append((src, dst))

    monkeypatch.setattr(os.path, 'exists', lambda path: dst_exists)
    monkeypatch.setattr('shutil.copy2', mock_copy2)
    monkeypatch.setattr(api, 'current_logger', logger)

    addupgradebootloader._copy_file(src_path, dst_path)

    assert copy2_calls == [(src_path, dst_path)]
    if dst_exists:
        assert 'The {} file already exists and its content will be overwritten.'.format(dst_path) in logger.dbgmsg

    assert 'Copying {} to {}'.format(src_path, dst_path) in logger.infomsg


def test_copy_file_error(monkeypatch):
    src_path = '/src/file.txt'
    dst_path = '/dst/file.txt'
    logger = logger_mocked()

    def mock_copy2_fail(src, dst):
        raise make_OSError(5)

    monkeypatch.setattr(os.path, 'exists', lambda path: False)
    monkeypatch.setattr('shutil.copy2', mock_copy2_fail)
    monkeypatch.setattr(api, 'current_logger', logger)

    with pytest.raises(StopActorExecutionError, match=r'I/O error\(5\)'):
        addupgradebootloader._copy_file(src_path, dst_path)


def test_get_userspace_info(monkeypatch):
    target_info_mock = TargetUserSpaceInfo(path='/USERSPACE', scratch='/SCRATCH', mounts='/MOUNTS')

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[target_info_mock]))

    result = addupgradebootloader._get_userspace_info()
    assert result == target_info_mock


def test_get_userspace_info_none(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))

    with pytest.raises(StopActorExecutionError, match='Could not retrieve TargetUserSpaceInfo'):
        addupgradebootloader._get_userspace_info()


def test_get_userspace_info_multiple(monkeypatch):
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        TargetUserSpaceInfo(path='/USERSPACE1', scratch='/SCRATCH1', mounts='/MOUNTS1'),
        TargetUserSpaceInfo(path='/USERSPACE2', scratch='/SCRATCH2', mounts='/MOUNTS2'),
    ]))

    addupgradebootloader._get_userspace_info()

    assert 'Unexpectedly received more than one TargetUserSpaceInfo message.' in logger.warnmsg


@pytest.mark.parametrize('exists', [True, False])
def test_ensure_clean_environment(monkeypatch, exists):
    rmtree_calls = []

    monkeypatch.setattr('os.path.exists', lambda path: exists)
    monkeypatch.setattr('shutil.rmtree', rmtree_calls.append)

    addupgradebootloader._ensure_clean_environment()

    assert rmtree_calls == ([addupgradebootloader.LEAPP_EFIDIR_CANONICAL_PATH] if exists else [])


def test_copy_grub_files(monkeypatch):
    copy_file_calls = []

    def mock_copy_file(src, dst):
        copy_file_calls.append((src, dst))

    monkeypatch.setattr(addupgradebootloader, '_copy_file', mock_copy_file)
    monkeypatch.setattr(os.path, 'exists', lambda path: True)

    addupgradebootloader._copy_grub_files(['required'], ['optional'])

    assert (
        os.path.join(addupgradebootloader.RHEL_EFIDIR_CANONICAL_PATH, 'required'),
        os.path.join(addupgradebootloader.LEAPP_EFIDIR_CANONICAL_PATH, 'required')
    ) in copy_file_calls
    assert (
        os.path.join(addupgradebootloader.RHEL_EFIDIR_CANONICAL_PATH, 'optional'),
        os.path.join(addupgradebootloader.LEAPP_EFIDIR_CANONICAL_PATH, 'optional')
    ) in copy_file_calls


def test_add_upgrade_boot_entry_no_efi_binary(monkeypatch):
    monkeypatch.setattr(os.path, 'exists', lambda path: False)

    efibootinfo_mock = MockEFIBootInfo([TEST_RHEL_EFI_ENTRY])
    with pytest.raises(StopActorExecutionError, match="Unable to detect upgrade UEFI binary file"):
        addupgradebootloader._add_upgrade_boot_entry(efibootinfo_mock)


def test_add_upgrade_boot_entry_already_exists(monkeypatch):
    monkeypatch.setattr(os.path, 'exists', lambda path: True)

    efibootinfo_mock = MockEFIBootInfo([TEST_RHEL_EFI_ENTRY, TEST_UPGRADE_EFI_ENTRY])

    with mock.patch(
        "leapp.libraries.common.efi.add_boot_entry"
    ) as add_boot_entry_mock:
        result = addupgradebootloader._add_upgrade_boot_entry(efibootinfo_mock)
        add_boot_entry_mock.assert_not_called()
        assert result == TEST_UPGRADE_EFI_ENTRY


def test_add_upgrade_boot_entry_success(monkeypatch):
    monkeypatch.setattr(os.path, 'exists', lambda path: True)

    def add_boot_entry_mocked(label, efi_path):
        assert label == addupgradebootloader.UPGRADE_EFI_ENTRY_LABEL
        assert efi_path == '\\EFI\\leapp\\shimaa64.efi'
        return TEST_UPGRADE_EFI_ENTRY

    monkeypatch.setattr(efi, 'add_boot_entry', add_boot_entry_mocked)

    efibootinfo_mock = MockEFIBootInfo([TEST_RHEL_EFI_ENTRY])
    result = addupgradebootloader._add_upgrade_boot_entry(efibootinfo_mock)
    assert result.label == addupgradebootloader.UPGRADE_EFI_ENTRY_LABEL


def test_process(monkeypatch):
    run_calls = []

    def mock_run(cmd):
        run_calls.append(cmd)

    target_info_mock = TargetUserSpaceInfo(path='/USERSPACE', scratch='/SCRATCH', mounts='/MOUNTS')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[target_info_mock]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(addupgradebootloader, 'run', mock_run)

    context_mock = IsolatedActionsMocked()
    monkeypatch.setattr(addupgradebootloader.mounting, 'NspawnActions', lambda *args, **kwargs: context_mock)

    monkeypatch.setattr(addupgradebootloader, '_copy_grub_files', lambda optional, required: None)

    efibootinfo_mock = MockEFIBootInfo([TEST_RHEL_EFI_ENTRY])
    monkeypatch.setattr(efi, 'EFIBootInfo', lambda: efibootinfo_mock)

    def mock_add_upgrade_boot_entry(efibootinfo):
        return TEST_UPGRADE_EFI_ENTRY

    monkeypatch.setattr(addupgradebootloader, '_add_upgrade_boot_entry', mock_add_upgrade_boot_entry)
    monkeypatch.setattr(efi, 'set_bootnext', lambda _: None)

    monkeypatch.setattr(addupgradebootloader, 'patch_efi_redhat_grubcfg_to_load_correct_grubenv',
                        lambda: None)

    addupgradebootloader.process()

    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1

    efibootentry_fields = ['boot_number', 'label', 'active', 'efi_bin_source']
    expected = ArmWorkaroundEFIBootloaderInfo(
            original_entry=EFIBootEntry(**{f: getattr(TEST_RHEL_EFI_ENTRY, f) for f in efibootentry_fields}),
            upgrade_entry=EFIBootEntry(**{f: getattr(TEST_UPGRADE_EFI_ENTRY, f) for f in efibootentry_fields}),
            upgrade_bls_dir=addupgradebootloader.UPGRADE_BLS_DIR,
            upgrade_entry_efi_path='/boot/efi/EFI/leapp/',
        )
    actual = api.produce.model_instances[0]
    assert actual == expected


@pytest.mark.parametrize('is_config_ok', (True, False))
def test_patch_grubcfg(is_config_ok, monkeypatch):

    expected_grubcfg_path = os.path.join(efi.EFI_MOUNTPOINT,
                                         addupgradebootloader.LEAPP_EFIDIR_CANONICAL_PATH,
                                         'grub.cfg')

    def isfile_mocked(path):
        assert expected_grubcfg_path == path
        return True

    def prepare_config_contents_mocked():
        return 'config contents'

    def write_config(path, contents):
        assert not is_config_ok  # We should write only when the config is not OK
        assert path == expected_grubcfg_path
        assert contents == 'config contents'

    monkeypatch.setattr(os.path, 'isfile', isfile_mocked)
    monkeypatch.setattr(addupgradebootloader, '_will_grubcfg_read_our_grubenv', lambda cfg_path: is_config_ok)
    monkeypatch.setattr(addupgradebootloader, '_prepare_config_contents', prepare_config_contents_mocked)
    monkeypatch.setattr(addupgradebootloader, '_write_config', write_config)
