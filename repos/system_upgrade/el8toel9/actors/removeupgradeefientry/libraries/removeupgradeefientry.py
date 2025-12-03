import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.firmware import efi
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import ArmWorkaroundEFIBootloaderInfo

EFI_MOUNTPOINT = '/boot/efi/'
LEAPP_EFIDIR_CANONICAL_PATH = os.path.join(EFI_MOUNTPOINT, 'EFI/leapp/')
RHEL_EFIDIR_CANONICAL_PATH = os.path.join(EFI_MOUNTPOINT, 'EFI/redhat/')


def get_workaround_efi_info():
    bootloader_info_msgs = api.consume(ArmWorkaroundEFIBootloaderInfo)
    bootloader_info = next(bootloader_info_msgs, None)
    if list(bootloader_info_msgs):
        api.current_logger().warning('Unexpectedly received more than one UpgradeEFIBootEntry message.')
    if not bootloader_info:
        raise StopActorExecutionError('Could not remove UEFI boot entry for the upgrade initramfs.',
                                      details={'details': 'Did not receive a message about the leapp-provided'
                                                          ' kernel and initramfs.'})
    return bootloader_info


def remove_upgrade_efi_entry():
    # we need to make sure /boot/efi/ is mounted before trying to remove the boot entry
    mount_points = ['/boot', '/boot/efi']
    for mp in mount_points:
        try:
            run(['/bin/mount', mp])
        except CalledProcessError:
            # partitions have been most likely already mounted
            pass

    bootloader_info = get_workaround_efi_info()

    upgrade_boot_number = bootloader_info.upgrade_entry.boot_number
    try:
        efi.remove_boot_entry(upgrade_boot_number)
    except efi.EFIError:
        api.current_logger().warning('Unable to remove Leapp upgrade efi entry.')

    try:
        run(['rm', '-rf', LEAPP_EFIDIR_CANONICAL_PATH])
    except CalledProcessError:
        api.current_logger().warning('Unable to remove Leapp upgrade efi files.')

    _remove_upgrade_blsdir(bootloader_info)

    original_boot_number = bootloader_info.original_entry.boot_number
    efi.set_bootnext(original_boot_number)

    # TODO: Move calling `mount -a` to a separate actor as it is not really
    # related to removing the upgrade boot entry. It's worth to call it after
    # removing the boot entry to avoid boot loop in case mounting fails.
    run(['/bin/mount', '-a'])


def _remove_upgrade_blsdir(bootloader_info):
    api.current_logger().debug('Removing upgrade BLS directory: {}'.format(bootloader_info.upgrade_bls_dir))
    try:
        shutil.rmtree(bootloader_info.upgrade_bls_dir)
    except OSError as error:
        # I tried, no can do at this point
        msg = 'Failed to remove upgrade BLS directory: {} with error {}'
        api.current_logger().debug(msg.format(bootloader_info.upgrade_bls_dir, error))
