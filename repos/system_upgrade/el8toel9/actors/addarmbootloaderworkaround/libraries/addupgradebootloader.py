import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.common.grub import (
    canonical_path_to_efi_format,
    EFIBootInfo,
    get_device_number,
    get_efi_device,
    get_efi_partition,
    GRUB2_BIOS_ENTRYPOINT,
    GRUB2_BIOS_ENV_FILE
)
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import ArmWorkaroundEFIBootloaderInfo, EFIBootEntry, TargetUserSpaceInfo

UPGRADE_EFI_ENTRY_LABEL = 'Leapp Upgrade'

ARM_SHIM_PACKAGE_NAME = 'shim-aa64'
ARM_GRUB_PACKAGE_NAME = 'grub2-efi-aa64'

EFI_MOUNTPOINT = '/boot/efi/'
LEAPP_EFIDIR_CANONICAL_PATH = os.path.join(EFI_MOUNTPOINT, 'EFI/leapp/')
RHEL_EFIDIR_CANONICAL_PATH = os.path.join(EFI_MOUNTPOINT, 'EFI/redhat/')

CONTAINER_DOWNLOAD_DIR = '/tmp_pkg_download_dir'


def _copy_file(src_path, dst_path):
    if os.path.exists(dst_path):
        api.current_logger().debug("The {} file already exists and its content will be overwritten.".format(dst_path))

    api.current_logger().info("Copying {} to {}".format(src_path, dst_path))
    try:
        shutil.copy2(src_path, dst_path)
    except (OSError, IOError) as err:
        raise StopActorExecutionError('I/O error({}): {}'.format(err.errno, err.strerror))


def process():
    userspace = _get_userspace_info()

    with mounting.NspawnActions(base_dir=userspace.path) as context:
        _ensure_clean_environment()

        # NOTE(dkubek): Assumes required shim-aa64 and grub2-efi-aa64 packages
        # have been installed
        context.copytree_from(RHEL_EFIDIR_CANONICAL_PATH, LEAPP_EFIDIR_CANONICAL_PATH)

        _copy_grub_files(['grubenv', 'grub.cfg'], ['user.cfg'])
        _link_grubenv_to_upgrade_entry()

        efibootinfo = EFIBootInfo()
        current_boot_entry = efibootinfo.entries[efibootinfo.current_bootnum]
        upgrade_boot_entry = _add_upgrade_boot_entry(efibootinfo)
        _set_bootnext(upgrade_boot_entry.boot_number)

        efibootentry_fields = ['boot_number', 'label', 'active', 'efi_bin_source']
        api.produce(
            ArmWorkaroundEFIBootloaderInfo(
                original_entry=EFIBootEntry(**{f: getattr(current_boot_entry, f) for f in efibootentry_fields}),
                upgrade_entry=EFIBootEntry(**{f: getattr(upgrade_boot_entry, f) for f in efibootentry_fields}),
            )
        )


def _get_userspace_info():
    msgs = api.consume(TargetUserSpaceInfo)

    userspace = next(msgs, None)
    if userspace is None:
        raise StopActorExecutionError('Could not retrieve TargetUserSpaceInfo!')

    if next(msgs, None):
        api.current_logger().warning('Unexpectedly received more than one TargetUserSpaceInfo message.')

    return userspace


def _ensure_clean_environment():
    if os.path.exists(LEAPP_EFIDIR_CANONICAL_PATH):
        shutil.rmtree(LEAPP_EFIDIR_CANONICAL_PATH)


def _copy_grub_files(required, optional):
    """
    Copy grub files from redhat/ dir to the /boot/efi/EFI/leapp/ dir.
    """

    all_files = required + optional
    for filename in all_files:
        src_path = os.path.join(RHEL_EFIDIR_CANONICAL_PATH, filename)
        dst_path = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, filename)

        if not os.path.exists(src_path):
            if filename in required:
                msg = 'Required file {} does not exists. Aborting.'.format(filename)
                raise StopActorExecutionError(msg)

            continue

        _copy_file(src_path, dst_path)


def _link_grubenv_to_upgrade_entry():
    upgrade_env_file = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, 'grubenv')
    upgrade_env_file_relpath = os.path.relpath(upgrade_env_file, GRUB2_BIOS_ENTRYPOINT)
    run(['ln', '--symbolic', '--force', upgrade_env_file_relpath, GRUB2_BIOS_ENV_FILE])


def _add_upgrade_boot_entry(efibootinfo):
    """
    Create a new UEFI bootloader entry with a upgrade label and bin file.

    If an entry for the label and bin file already exists no new entry
    will be created.

    Return the upgrade efi entry (EFIEntry).
    """

    dev_number = get_device_number(get_efi_partition())
    blk_dev = get_efi_device()

    tmp_efi_path = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, 'shimaa64.efi')
    if os.path.exists(tmp_efi_path):
        efi_path = canonical_path_to_efi_format(tmp_efi_path)
    else:
        raise StopActorExecutionError('Unable to detect upgrade UEFI binary file.')

    upgrade_boot_entry = _get_upgrade_boot_entry(efibootinfo, efi_path, UPGRADE_EFI_ENTRY_LABEL)
    if upgrade_boot_entry is not None:
        return upgrade_boot_entry

    cmd = [
        "/usr/sbin/efibootmgr",
        "--create",
        "--disk",
        blk_dev,
        "--part",
        str(dev_number),
        "--loader",
        efi_path,
        "--label",
        UPGRADE_EFI_ENTRY_LABEL,
    ]

    try:
        run(cmd)
    except CalledProcessError:
        raise StopActorExecutionError('Unable to add a new UEFI bootloader entry for upgrade.')

    # Sanity check new boot entry has been added
    efibootinfo_new = EFIBootInfo()
    upgrade_boot_entry = _get_upgrade_boot_entry(efibootinfo_new, efi_path, UPGRADE_EFI_ENTRY_LABEL)
    if upgrade_boot_entry is None:
        raise StopActorExecutionError('Unable to find the new UEFI bootloader entry after adding it.')

    return upgrade_boot_entry


def _get_upgrade_boot_entry(efibootinfo, efi_path, label):
    """
    Get the UEFI boot entry with label `label` and EFI binary path `efi_path`

    Return EFIBootEntry or None if not found.
    """

    for entry in efibootinfo.entries.values():
        if entry.label == label and efi_path in entry.efi_bin_source:
            return entry

    return None


def _set_bootnext(boot_number):
    """
    Set the BootNext UEFI entry to `boot_number`.
    """

    api.current_logger().debug('Setting {} as BootNext'.format(boot_number))
    try:
        run(['/usr/sbin/efibootmgr', '--bootnext', boot_number])
    except CalledProcessError:
        raise StopActorExecutionError('Could not set boot entry {} as BootNext.'.format(boot_number))
