import errno
import os

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import efi
from leapp.libraries.common.config import architecture, get_source_distro_id, get_target_distro_id, is_conversion
from leapp.libraries.common.distro import distro_id_to_pretty_name, get_distro_efidir_canon_path
from leapp.libraries.stdlib import api


def _get_target_efi_bin_path():
    # Sorted by priority.
    # NOTE: The shim-x64 package providing the shimx64.efi binary can be removed when
    # not using secure boot, grubx64.efi should always be present (provided by
    # grub-efi-x64).
    # WARN: However it is expected to have the shim installed on the system to comply
    # with the official guidelines.
    #
    # TODO: There are usually 2 more shim* files which appear unused on a fresh system:
    # - shim.efi - seems like it's the same as shimx64.efi
    # - shim64-<distro>.efi - ???
    # What about them?
    efibins_by_arch = {
        architecture.ARCH_X86_64: ("shimx64.efi", "grubx64.efi"),
        architecture.ARCH_ARM64: ("shimaa64.efi", "grubaa64.efi"),
    }

    arch = api.current_actor().configuration.architecture
    for filename in efibins_by_arch[arch]:
        efi_dir = get_distro_efidir_canon_path(get_target_distro_id())
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

    existing_entry = efi.get_boot_entry(efibootinfo, label, efi_bin_path)
    if existing_entry:
        api.current_logger().debug(
            "The '{}' UEFI bootloader entry is already present.".format(label)
        )
        return existing_entry

    return efi.add_boot_entry(label, efi_bin_path)


def _remove_boot_entry_for_source(efibootinfo):
    efibootinfo_fresh = efi.EFIBootInfo()
    source_entry = efibootinfo_fresh.entries.get(efibootinfo.current_bootnum, None)

    if not source_entry:
        api.current_logger().debug(
            "The currently booted source distro EFI boot entry has been already"
            " removed since the target entry has been added, skipping removal."
        )
        return

    original_source_entry = efibootinfo.entries[source_entry.boot_number]

    if source_entry != original_source_entry:
        api.current_logger().debug(
            "The boot entry with current bootnum has changed since the target"
            " distro entry has been added, skipping removal."
        )
        return

    efi.remove_boot_entry(source_entry.boot_number)


def _try_remove_source_efi_dir():
    """
    Try to remove the source distro EFI directory

    The directory is not reported if it's not empty to preserve potential
    custom files. In such a case a post upgrade report is produced informing
    user to handle the leftover files.
    """
    efi_dir_source = get_distro_efidir_canon_path(get_source_distro_id())
    if not os.path.exists(efi_dir_source):
        api.current_logger().debug(
            "Source distro EFI directory at {} does not exist, skipping removal.".format(efi_dir_source)
        )
        return

    target_efi_dir = get_distro_efidir_canon_path(get_target_distro_id())
    if efi_dir_source == target_efi_dir:
        api.current_logger().debug(
            "Source and target distros use the same '{}' EFI directory.".format(efi_dir_source)
        )
        return

    try:
        os.rmdir(efi_dir_source)
        api.current_logger().debug(
            "Deleted source system EFI directory at {}".format(efi_dir_source)
        )
    except FileNotFoundError:
        api.current_logger().debug(
            "Couldn't remove the source system EFI directory at {}: the directory no longer exists".format(
                efi_dir_source
            )
        )
    except OSError as e:
        if e.errno == errno.ENOTEMPTY:
            api.current_logger().debug(
                "Didn't remove the source EFI directory {}, it does not exist".format(
                    efi_dir_source
                )
            )
            summary = (
                "During the upgrade, the EFI binaries and grub configuration files"
                f" were migrated from the source OS EFI directory {efi_dir_source}"
                f" to the target OS EFI directory {target_efi_dir}."
                f" Leftover files were detected in {target_efi_dir}, review them"
                " and migrate them manually."
            )
            reporting.create_report([
                reporting.Title("Review leftover files in the source OS EFI directory"),
                reporting.Summary(summary),
                reporting.Groups([
                    reporting.Groups.BOOT,
                    reporting.Groups.POST,
                ]),
                reporting.Severity(reporting.Severity.LOW),
            ])
        else:
            api.current_logger().error(
                "Failed to remove the source system EFI directory at {}: {}".format(
                    efi_dir_source, e
                )
            )
            summary = (
                f"Removal of the source system EFI directory at {efi_dir_source} failed."
                " Remove the directory manually if present."
            )
            reporting.create_report([
                reporting.Title("Failed to remove source system EFI directory"),
                reporting.Summary(summary),
                reporting.Groups([
                    reporting.Groups.BOOT,
                    reporting.Groups.FAILURE,
                    reporting.Groups.POST,
                ]),
                reporting.Severity(reporting.Severity.LOW),
            ])


def _replace_boot_entries():
    try:
        efibootinfo = efi.EFIBootInfo()
        target_entry = _add_boot_entry_for_target(efibootinfo)
        # NOTE: this isn't strictly necessary as UEFI should set the next entry
        # to be the first in the BootOrder. This is a workaround to make sure
        # the "efi_finalization_fix" actor doesn't attempt to set BootNext to
        # the original entry which will be deleted below.
        efi.set_bootnext(target_entry.boot_number)
    except efi.EFIError as e:
        raise StopActorExecutionError(
            "Failed to add UEFI boot entry for the target system",
            details={"details": str(e)},
        )

    # NOTE: Some UEFI implementations, such as OVMF used in qemu, automatically
    # add entries for EFI directories. Though the entry is named after the EFI
    # directory (so "redhat" on RHEL). However if the UEFI doesn't add an entry
    # after we fail to do so, it might render the OS "unbootable".
    # Let's keep the source entry and directory if we can't add the target entry as a
    # backup.

    _try_remove_source_efi_dir()

    try:
        # doesn't matter if the removal of source EFI dir failed, we don't want
        # the source entry, we have the new one for target
        _remove_boot_entry_for_source(efibootinfo)
    except efi.EFIError as e:
        api.current_logger().error("Failed to remove source distro EFI boot entry: {}".format(e))

        # This is low severity, some UEFIs will automatically remove an entry
        # whose EFI binary no longer exists at least OVMF, used by qemu, does.
        summary = (
            "Removal of the source system UEFI boot entry failed."
            " Check UEFI boot entries and manually remove it if it's still present."
        )
        reporting.create_report(
            [
                reporting.Title("Failed to remove source system EFI boot entry"),
                reporting.Summary(summary),
                reporting.Groups(
                    [
                        reporting.Groups.BOOT,
                        reporting.Groups.FAILURE,
                        reporting.Groups.POST,
                    ]
                ),
                reporting.Severity(reporting.Severity.LOW),
            ]
        )


def process():
    if not is_conversion():
        return

    if not architecture.matches_architecture(architecture.ARCH_X86_64, architecture.ARCH_ARM64):
        return

    if not efi.is_efi():
        return

    # NOTE no need to check whether we have the efibootmgr binary, the
    # efi_check_boot actor does

    _replace_boot_entries()
