import os
import shutil

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.distro import distro_id_to_pretty_name
from leapp.libraries.common.firmware import is_efi, efi
from leapp.libraries.stdlib import api


def _get_target_efi_bin_path():
    # TODO aarch64

    # Sorted by priority.
    # The shim-x64 package providing the shimx64.efi binary can be removed when
    # not using secure boot, however grubx64.efi should be present (provided by
    # grub-efi-x64, otherwise the system is can be considered broken
    #
    # TODO: There are usually 2 more shim* files which appear unused on a fresh system:
    # - shim.efi - seems like it's the same as shimx64.efi
    # - shim64-<distro>.efi - ???
    # What about them?
    for filename in ("shimx64.efi", "grubx64.efi"):
        efi_dir = efi.get_distro_efidir_canon_path(get_target_distro_id())
        canon_path = os.path.join(efi_dir, filename)
        if os.path.exists(canon_path):
            return efi.canonical_path_to_efi_format(canon_path)

    return None


def _add_boot_entry_for_target(efibootinfo):
    """
    Create a new UEFI bootloader entry for the target system.

    Return the newly created bootloader entry.
    """
    efi_bin_path = _get_target_efi_bin_path()
    if not efi_bin_path:
        # this is a fatal error as at least one of the possible EFI binaries
        # should be present
        raise efi.EFIError("Unable to detect any UEFI binary file.")

    label = distro_id_to_pretty_name(get_target_distro_id())

    if efi.get_boot_entry(efibootinfo, efi_bin_path, label):
        api.current_logger().debug(
            "The '{}' UEFI bootloader entry is already present.".format(label)
        )
        return efibootinfo

    return efi.add_boot_entry(label, efi_bin_path)


def _remove_boot_entry_for_source(efibootinfo):
    efibootinfo_fresh = efi.EFIBootInfo()
    source_entry = efibootinfo_fresh.entries.get(efibootinfo.current_bootnum, None)
    original_source_entry = efibootinfo.entries[source_entry.boot_number]

    if not source_entry:
        api.current_logger().debug(
            "The currently booted source distro EFI boot entry has been already"
            " removed since the target entry has been added, skipping removal."
        )
        return
    if source_entry != original_source_entry:
        api.current_logger().debug(
            "The boot entry with current bootnum has changed since the target"
            " distro entry has been added, skipping removal."
        )
        return

    efi.remove_boot_entry(source_entry.boot_number)


def _try_remove_source_efi_dir():
    efi_dir_source = efi.get_distro_efidir_canon_path(get_source_distro_id())
    if not os.path.exists(efi_dir_source):
        api.current_logger().debug(
            "Source distro EFI directory at {} does not exists, skipping removal.".format(efi_dir_source)
        )
        return

    target_efi_dir = efi.get_distro_efidir_canon_path(get_target_distro_id())
    if efi_dir_source == target_efi_dir:
        api.current_logger().debug(
            "Source and target distros use the same '{}' EFI directory.".format(efi_dir_source)
        )
        return

    try:
        shutil.rmtree(efi_dir_source)
    except OSError as e:
        api.current_logger().error(
            "Failed to remove the source system EFI directory at {}: {}".format(
                efi_dir_source, e
            )
        )
        summary = (
            "Removal of the source system EFI directory at {} failed."
            " Remove the directory manually if present."
        ).format(efi_dir_source)
        reporting.create_report([
            reporting.Title('Failed to remove source system EFI directory'),
            reporting.Summary(summary),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Severity(reporting.Severity.LOW),
        ])

    api.current_logger().debug(
        "Deleted source system EFI directory at {}".format(efi_dir_source)
    )


def process():
    if get_source_distro_id() == get_target_distro_id():
        return

    if not is_efi():
        return

    # NOTE no need to check whether we have the efibootmgr binary, the
    # efi_check_boot actor does

    try:
        efibootinfo = efi.EFIBootInfo()
        target_entry = _add_boot_entry_for_target(efibootinfo)
    except efi.EFIError as e:
        raise StopActorExecutionError(
            "Failed to add UEFI boot entry for the target system",
            details={"details": str(e)},
        )

    # NOTE: Some UEFI implementations, such as OVMF used in qemu, automatically
    # add entries for EFI directories. Though the entry is named after the EFI
    # directory (so "redhat" on RHEL). However if the UEFI doesn't add an entry
    # after we fail to do so, it might render the OS "unbootable". Let's keep
    # the source entry and directory if we can't add the target entry as a
    # backup.

    _try_remove_source_efi_dir()

    try:
        _remove_boot_entry_for_source(efibootinfo)
    except efi.EFIError as e:
        api.current_logger().error("Failed to remove source distro EFI boot entry: {}".format(e))

        # This is low severity, some UEFIs will automatically remove an entry
        # whose EFI binary no longer exists, at least OVMF, used by qemu, does.
        summary = (
            "Removal of the source system UEFI boot entry failed."
            " Check UEFI boot entries and manually remove it if it's still present."
        )
        reporting.create_report([
            reporting.Title('Failed to remove source system EFI boot entry'),
            reporting.Summary(summary),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Severity(reporting.Severity.LOW),
        ])
