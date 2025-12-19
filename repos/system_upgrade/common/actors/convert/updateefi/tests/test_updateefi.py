import copy
import errno
import os
import types
from unittest import mock

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import updateefi
from leapp.libraries.common import efi
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api


@pytest.fixture
def mock_logger():
    with mock.patch(
        "leapp.libraries.stdlib.api.current_logger", new_callable=logger_mocked
    ) as mock_logger:
        yield mock_logger


@pytest.fixture
def mock_create_report():
    with mock.patch(
        "leapp.reporting.create_report", new_callable=create_report_mocked
    ) as mock_create_report:
        yield mock_create_report


@pytest.mark.parametrize(
    "arch, exist, expect",
    [
        (architecture.ARCH_X86_64, ["shimx64.efi", "grubx64.efi"], r"\EFI\redhat\shimx64.efi"),
        (architecture.ARCH_X86_64, ["shimx64.efi"], r"\EFI\redhat\shimx64.efi"),
        (architecture.ARCH_X86_64, ["grubx64.efi"], r"\EFI\redhat\grubx64.efi"),
        (architecture.ARCH_X86_64, [], None),

        (architecture.ARCH_ARM64, ["shimaa64.efi", "grubaa64.efi"], r"\EFI\redhat\shimaa64.efi"),
        (architecture.ARCH_ARM64, ["shimaa64.efi"], r"\EFI\redhat\shimaa64.efi"),
        (architecture.ARCH_ARM64, ["grubaa64.efi"], r"\EFI\redhat\grubaa64.efi"),
        (architecture.ARCH_ARM64, [], None),
    ]
)
def test__get_target_efi_bin_path(monkeypatch, arch, exist, expect):
    # distro is not important, just make it look like conversion
    curr_actor = CurrentActorMocked(arch=arch, src_distro="centos", dst_distro="rhel")
    monkeypatch.setattr(api, "current_actor", curr_actor)

    def mock_exists(path):
        efidir = "/boot/efi/EFI/redhat"
        return path in [os.path.join(efidir, p) for p in exist]

    monkeypatch.setattr(os.path, "exists", mock_exists)

    actual = updateefi._get_target_efi_bin_path()
    assert actual == expect


TEST_ADD_ENTRY_INPUTS = [
    ("Red Hat Enterprise Linux", r"\EFI\redhat\shimx64.efi"),
    ("Red Hat Enterprise Linux", r"\EFI\redhat\grubx64.efi"),
    ("Centos Stream", r"\EFI\centos\grubx64.efi"),
]


@pytest.mark.parametrize("label, efi_bin_path", TEST_ADD_ENTRY_INPUTS)
@mock.patch("leapp.libraries.common.efi.get_boot_entry")
@mock.patch("leapp.libraries.common.efi.add_boot_entry")
def test__add_boot_entry_for_target(
    mock_add_boot_entry, mock_get_boot_entry, monkeypatch, label, efi_bin_path
):
    # need to mock this but it's unused because distro_id_to_pretty_name is mocked
    monkeypatch.setattr(api, "current_actor", CurrentActorMocked(dst_distro="whatever"))
    monkeypatch.setattr(updateefi, "distro_id_to_pretty_name", lambda _distro: label)
    monkeypatch.setattr(updateefi, "_get_target_efi_bin_path", lambda: efi_bin_path)

    mock_efibootinfo = mock.MagicMock(name="EFIBootInfo_instance")
    entry = efi.EFIBootLoaderEntry("0003", label, True, efi_bin_path)
    mock_get_boot_entry.return_value = None
    mock_add_boot_entry.return_value = entry

    assert entry == updateefi._add_boot_entry_for_target(mock_efibootinfo)

    mock_get_boot_entry.assert_called_once_with(mock_efibootinfo, label, efi_bin_path)
    mock_add_boot_entry.assert_called_once_with(label, efi_bin_path)


@pytest.mark.parametrize("label, efi_bin_path", TEST_ADD_ENTRY_INPUTS)
@mock.patch("leapp.libraries.common.efi.get_boot_entry")
@mock.patch("leapp.libraries.common.efi.add_boot_entry")
def test__add_boot_entry_for_target_already_exists(
    mock_add_boot_entry, mock_get_boot_entry, monkeypatch, label, efi_bin_path
):
    # need to mock this but it's unused because distro_id_to_pretty_name is mocked
    monkeypatch.setattr(api, "current_actor", CurrentActorMocked(dst_distro="whatever"))
    monkeypatch.setattr(updateefi, "distro_id_to_pretty_name", lambda _distro: label)
    monkeypatch.setattr(updateefi, "_get_target_efi_bin_path", lambda: efi_bin_path)

    mock_efibootinfo = mock.MagicMock(name="EFIBootInfo_instance")
    entry = efi.EFIBootLoaderEntry("0003", label, True, efi_bin_path)
    mock_get_boot_entry.return_value = entry

    out = updateefi._add_boot_entry_for_target(mock_efibootinfo)

    assert out == entry
    mock_get_boot_entry.assert_called_once_with(mock_efibootinfo, label, efi_bin_path)
    mock_add_boot_entry.assert_not_called()


def test__add_boot_entry_for_target_no_efi_bin(monkeypatch):
    monkeypatch.setattr(updateefi, "_get_target_efi_bin_path", lambda: None)

    with pytest.raises(efi.EFIError, match="Unable to detect any UEFI binary file."):
        mock_efibootinfo = mock.MagicMock(name="EFIBootInfo_instance")
        updateefi._add_boot_entry_for_target(mock_efibootinfo)


class MockEFIBootInfo:

    def __init__(self, entries, current_bootnum=None):
        # just to have some entries even when we don't need the entries
        other_entry = efi.EFIBootLoaderEntry(
            "0001",
            "UEFI: Built-in EFI Shell",
            True,
            "VenMedia(5023b95c-db26-429b-a648-bd47664c8012)..BO",
        )
        entries = entries + [other_entry]

        self.boot_order = tuple(entry.boot_number for entry in entries)
        self.current_bootnum = current_bootnum or self.boot_order[0]
        self.next_bootnum = None
        self.entries = {entry.boot_number: entry for entry in entries}


TEST_SOURCE_ENTRY = efi.EFIBootLoaderEntry(
    "0002", "Centos Stream", True, r"File(\EFI\centos\shimx64.efi)"
)
TEST_TARGET_ENTRY = efi.EFIBootLoaderEntry(
    "0003", "Red Hat Enterprise Linux", True, r"File(\EFI\redhat\shimx64.efi)"
)


@mock.patch("leapp.libraries.common.efi.remove_boot_entry")
@mock.patch("leapp.libraries.common.efi.EFIBootInfo")
def test__remove_boot_entry_for_source(
    mock_efibootinfo,
    mock_remove_boot_entry,
):
    efibootinfo = MockEFIBootInfo([TEST_SOURCE_ENTRY], current_bootnum="0002")
    mock_efibootinfo.return_value = MockEFIBootInfo(
        [TEST_TARGET_ENTRY, TEST_SOURCE_ENTRY], current_bootnum="0002"
    )

    updateefi._remove_boot_entry_for_source(efibootinfo)

    mock_efibootinfo.assert_called_once()
    mock_remove_boot_entry.assert_called_once_with("0002")


@mock.patch("leapp.libraries.common.efi.remove_boot_entry")
@mock.patch("leapp.libraries.common.efi.EFIBootInfo")
def test__remove_boot_entry_for_source_no_longer_exists(
    mock_efibootinfo, mock_remove_boot_entry, mock_logger
):
    efibootinfo = MockEFIBootInfo([TEST_SOURCE_ENTRY], current_bootnum="0002")
    mock_efibootinfo.return_value = MockEFIBootInfo(
        [TEST_TARGET_ENTRY], current_bootnum="0002"
    )

    updateefi._remove_boot_entry_for_source(efibootinfo)

    msg = (
        "The currently booted source distro EFI boot entry has been already"
        " removed since the target entry has been added, skipping removal."
    )
    assert msg in mock_logger.dbgmsg
    mock_efibootinfo.assert_called_once()
    mock_remove_boot_entry.assert_not_called()


@mock.patch("leapp.libraries.common.efi.remove_boot_entry")
@mock.patch("leapp.libraries.common.efi.EFIBootInfo")
def test__remove_boot_entry_for_source_has_changed(
    mock_efibootinfo, mock_remove_boot_entry, mock_logger
):
    efibootinfo = MockEFIBootInfo([TEST_SOURCE_ENTRY], current_bootnum="0002")
    modified_source_entry = copy.copy(TEST_SOURCE_ENTRY)
    modified_source_entry.efi_bin_source = r"File(\EFI\centos\grubx64.efi)"
    mock_efibootinfo.return_value = MockEFIBootInfo(
        [TEST_TARGET_ENTRY, modified_source_entry], current_bootnum="0002"
    )

    updateefi._remove_boot_entry_for_source(efibootinfo)

    msg = (
        "The boot entry with current bootnum has changed since the target"
        " distro entry has been added, skipping removal."
    )
    assert msg in mock_logger.dbgmsg
    mock_efibootinfo.assert_called_once()
    mock_remove_boot_entry.assert_not_called()


class TestRemoveSourceEFIDir:
    SOURCE_EFIDIR = "/boot/efi/EFI/centos"
    TARGET_EFIDIR = "/boot/efi/EFI/redhat"

    @pytest.fixture(autouse=True)
    def mock_current_actor(self):  # pylint:disable=no-self-use
        with mock.patch("leapp.libraries.stdlib.api.current_actor") as mock_current_actor:
            mock_current_actor.return_value = CurrentActorMocked(
                src_distro="centos", dst_distro="redhat"
            )
            yield

    @mock.patch("os.path.exists")
    @mock.patch("leapp.libraries.actor.updateefi.get_distro_efidir_canon_path")
    @mock.patch("os.rmdir")
    def test_success(
        self, mock_rmdir, mock_efidir_path, mock_exists, mock_logger
    ):
        mock_efidir_path.side_effect = [self.SOURCE_EFIDIR, self.TARGET_EFIDIR]

        updateefi._try_remove_source_efi_dir()

        mock_exists.assert_called_once_with(self.SOURCE_EFIDIR)
        mock_rmdir.assert_called_once_with(self.SOURCE_EFIDIR)
        msg = f"Deleted source system EFI directory at {self.SOURCE_EFIDIR}"
        assert msg in mock_logger.dbgmsg

    @mock.patch("os.path.exists")
    @mock.patch("leapp.libraries.actor.updateefi.get_distro_efidir_canon_path")
    @mock.patch("os.rmdir")
    def test__efi_dir_does_not_exist(
        self, mock_rmdir, mock_efidir_path, mock_exists, mock_logger
    ):
        mock_efidir_path.return_value = self.SOURCE_EFIDIR
        mock_exists.return_value = False

        updateefi._try_remove_source_efi_dir()

        mock_exists.assert_called_once_with(self.SOURCE_EFIDIR)
        mock_rmdir.assert_not_called()
        msg = f"Source distro EFI directory at {self.SOURCE_EFIDIR} does not exist, skipping removal."
        assert msg in mock_logger.dbgmsg

    @mock.patch("os.path.exists")
    @mock.patch("leapp.libraries.actor.updateefi.get_distro_efidir_canon_path")
    @mock.patch("os.rmdir")
    def test_source_efi_dir_same_as_target(
        self, mock_rmdir, mock_efidir_path, mock_exists, mock_logger
    ):
        """
        Source and target dirs use the same directory
        """
        mock_efidir_path.side_effect = [self.TARGET_EFIDIR, self.TARGET_EFIDIR]
        mock_exists.return_value = True

        updateefi._try_remove_source_efi_dir()

        mock_exists.assert_called_once_with(self.TARGET_EFIDIR)
        mock_rmdir.assert_not_called()
        msg = f"Source and target distros use the same '{self.TARGET_EFIDIR}' EFI directory."
        assert msg in mock_logger.dbgmsg

    @mock.patch("os.path.exists")
    @mock.patch("leapp.libraries.actor.updateefi.get_distro_efidir_canon_path")
    @mock.patch("os.rmdir")
    def test_rmdir_fail(
        self, mock_rmdir, mock_efidir_path, mock_exists, mock_logger, mock_create_report
    ):
        """
        Test removal failures
        """
        mock_efidir_path.side_effect = [self.SOURCE_EFIDIR, self.TARGET_EFIDIR]
        mock_rmdir.side_effect = OSError

        updateefi._try_remove_source_efi_dir()

        mock_exists.assert_called_once_with(self.SOURCE_EFIDIR)
        mock_rmdir.assert_called_once_with(self.SOURCE_EFIDIR)
        msg = f"Failed to remove the source system EFI directory at {self.SOURCE_EFIDIR}"
        assert msg in mock_logger.errmsg[0]
        assert mock_create_report.called == 1
        title = "Failed to remove source system EFI directory"
        assert mock_create_report.report_fields["title"] == title

    @mock.patch("os.path.exists")
    @mock.patch("leapp.libraries.actor.updateefi.get_distro_efidir_canon_path")
    @mock.patch("os.rmdir")
    def test_dir_no_longer_exists_failed_rmdir(
        self, mock_rmdir, mock_efidir_path, mock_exists, mock_logger
    ):
        mock_efidir_path.side_effect = [self.SOURCE_EFIDIR, self.TARGET_EFIDIR]
        mock_rmdir.side_effect = FileNotFoundError(
            2, "No such file or directory", self.SOURCE_EFIDIR
        )

        updateefi._try_remove_source_efi_dir()

        mock_exists.assert_called_once_with(self.SOURCE_EFIDIR)
        mock_rmdir.assert_called_once_with(self.SOURCE_EFIDIR)
        msg = (
            "Couldn't remove the source system EFI directory at"
            f" {self.SOURCE_EFIDIR}: the directory no longer exists"
        )
        assert msg in mock_logger.dbgmsg[0]

    @mock.patch("os.path.exists")
    @mock.patch("leapp.libraries.actor.updateefi.get_distro_efidir_canon_path")
    @mock.patch("os.rmdir")
    def test_dir_not_empty(
        self, mock_rmdir, mock_efidir_path, mock_exists, mock_logger, mock_create_report
    ):
        """
        Test that the directory is not removed if there are any leftover files

        The distro provided files in the efi dir are usually removed during the RPM
        upgrade transaction (shim and grub own them). If there are any leftover
        files, such as custom user files, the directory should be preserved and
        report created.
        """
        mock_efidir_path.side_effect = [self.SOURCE_EFIDIR, self.TARGET_EFIDIR]
        mock_rmdir.side_effect = OSError(
            errno.ENOTEMPTY, os.strerror(errno.ENOTEMPTY), self.SOURCE_EFIDIR
        )

        updateefi._try_remove_source_efi_dir()

        mock_rmdir.assert_called_once_with(self.SOURCE_EFIDIR)
        mock_exists.assert_called_once_with(self.SOURCE_EFIDIR)
        msg = "Didn't remove the source EFI directory {}, it does not exist".format(
            self.SOURCE_EFIDIR
        )
        assert msg in mock_logger.dbgmsg[0]
        assert mock_create_report.called == 1
        title = "Review leftover files in the source OS EFI directory"
        assert mock_create_report.report_fields["title"] == title


@pytest.mark.parametrize(
    "is_conversion, arch, is_efi, should_skip",
    [
        # conversion, is efi
        (True, architecture.ARCH_X86_64, True, False),
        (True, architecture.ARCH_ARM64, True, False),
        (True, architecture.ARCH_PPC64LE, True, True),
        (True, architecture.ARCH_S390X, True, True),
        # conversion, not efi
        (True, architecture.ARCH_X86_64, False, True),
        (True, architecture.ARCH_ARM64, False, True),
        (True, architecture.ARCH_PPC64LE, False, True),
        (True, architecture.ARCH_S390X, False, True),
        # not conversion, is efi
        (False, architecture.ARCH_X86_64, True, True),
        (False, architecture.ARCH_ARM64, True, True),
        (False, architecture.ARCH_PPC64LE, True, True),
        (False, architecture.ARCH_S390X, True, True),
        # not conversion, not efi
        (False, architecture.ARCH_X86_64, False, True),
        (False, architecture.ARCH_ARM64, False, True),
        (False, architecture.ARCH_PPC64LE, False, True),
        (False, architecture.ARCH_S390X, False, True),
    ],
)
@mock.patch("leapp.libraries.actor.updateefi._replace_boot_entries")
def test_process_skip(
    mock_replace_boot_entries, monkeypatch, is_conversion, arch, is_efi, should_skip
):
    monkeypatch.setattr(api, "current_actor", CurrentActorMocked(arch=arch))
    monkeypatch.setattr(updateefi, "is_conversion", lambda: is_conversion)
    monkeypatch.setattr(efi, "is_efi", lambda: is_efi)

    updateefi.process()

    if should_skip:
        mock_replace_boot_entries.assert_not_called()
    else:
        mock_replace_boot_entries.assert_called_once()


class TestReplaceBootEntries:

    @pytest.fixture
    def mocks(self):  # pylint:disable=no-self-use
        UPDATE_EFI = 'leapp.libraries.actor.updateefi'
        EFI_LIB = 'leapp.libraries.common.efi'
        with mock.patch(f'{UPDATE_EFI}._try_remove_source_efi_dir') as remove_source_dir, \
             mock.patch(f'{UPDATE_EFI}._remove_boot_entry_for_source') as remove_source_entry, \
             mock.patch(f'{UPDATE_EFI}._add_boot_entry_for_target') as add_target_entry, \
             mock.patch(f'{EFI_LIB}.set_bootnext') as set_bootnext, \
             mock.patch(f'{EFI_LIB}.EFIBootInfo') as efibootinfo:

            # default for happy path
            efibootinfo_obj = mock.MagicMock(name="EFIBootInfo_instance")
            efibootinfo.return_value = efibootinfo_obj

            entry = mock.MagicMock(name="target_entry")
            entry.boot_number = "0003"
            add_target_entry.return_value = entry

            yield types.SimpleNamespace(
                EFIBootInfo=efibootinfo,
                set_bootnext=set_bootnext,
                add_boot_entry_for_target=add_target_entry,
                try_remove_source_efi_dir=remove_source_dir,
                remove_boot_entry_for_source=remove_source_entry,
                logger=mock_logger,
            )

    def test__fail_remove_source_entry(  # pylint:disable=no-self-use
        self, mocks, mock_logger, mock_create_report
    ):
        mocks.remove_boot_entry_for_source.side_effect = efi.EFIError

        updateefi._replace_boot_entries()

        msg = "Failed to remove source distro EFI boot entry"
        assert msg in mock_logger.errmsg[0]

        assert mock_create_report.called == 1
        title = "Failed to remove source system EFI boot entry"
        assert mock_create_report.report_fields["title"] == title

    @pytest.mark.parametrize(
        "which_fail", ["EFIBootInfo", "add_target", "set_bootnext"]
    )
    def test__fail_add_target_entry(  # pylint:disable=no-self-use
        self, mocks, mock_logger, mock_create_report, which_fail
    ):
        if which_fail == "EFIBootInfo":
            mocks.EFIBootInfo.side_effect = efi.EFIError
        elif which_fail == "add_target":
            mocks.add_boot_entry_for_target.side_effect = efi.EFIError
        elif which_fail == "set_bootnext":
            mocks.set_bootnext.side_effect = efi.EFIError

        with pytest.raises(StopActorExecutionError):
            updateefi._replace_boot_entries()

        mocks.try_remove_source_efi_dir.assert_not_called()
        mocks.remove_boot_entry_for_source.assert_not_called()
        assert not mock_create_report.called

    def test__replace_boot_entries_success(  # pylint:disable=no-self-use
        self, mocks, mock_logger
    ):
        """Test that operations are carried out in the right order"""
        mgr = mock.MagicMock()
        mgr.attach_mock(mocks.EFIBootInfo, "EFIBootInfo")
        mgr.attach_mock(mocks.set_bootnext, "set_bootnext")
        mgr.attach_mock(mocks.add_boot_entry_for_target, "add_target_entry")
        mgr.attach_mock(mocks.remove_boot_entry_for_source, "remove_source_entry")
        mgr.attach_mock(mocks.try_remove_source_efi_dir, "remove_source_efidir")

        updateefi._replace_boot_entries()

        expected_sequence = [
            mock.call.EFIBootInfo(),
            mock.call.add_target_entry(efi.EFIBootInfo.return_value),
            mock.call.set_bootnext(mocks.add_boot_entry_for_target.return_value.boot_number),
            mock.call.remove_source_efidir(),
            mock.call.remove_source_entry(efi.EFIBootInfo.return_value),
        ]
        assert mgr.mock_calls == expected_sequence
