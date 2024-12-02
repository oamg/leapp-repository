import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.grub import GRUB2_BIOS_ENTRYPOINT, GRUB2_BIOS_ENV_FILE
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

    _copy_grub_files(['grubenv', 'grub.cfg'], ['user.cfg'])
    _link_grubenv_to_rhel_entry()

    upgrade_boot_number = bootloader_info.upgrade_entry.boot_number
    try:
        run([
            '/usr/sbin/efibootmgr',
            '--delete-bootnum',
            '--bootnum',
            upgrade_boot_number
        ])
    except CalledProcessError:
        api.current_logger().warning('Unable to remove Leapp upgrade efi entry.')

    try:
        run(['rm', '-rf', LEAPP_EFIDIR_CANONICAL_PATH])
    except CalledProcessError:
        api.current_logger().warning('Unable to remove Leapp upgrade efi files.')

    # Reload EFI info, boot order has changed as Leapp upgrade efi entry was removed
    bootloader_info = get_workaround_efi_info()
    original_boot_number = bootloader_info.original_entry.boot_number
    run(['/usr/sbin/efibootmgr', '--bootnext', original_boot_number])

    # TODO: Move calling `mount -a` to a separate actor as it is not really
    # related to removing the upgrade boot entry. It's worth to call it after
    # removing the boot entry to avoid boot loop in case mounting fails.
    run(['/bin/mount', '-a'])


def _link_grubenv_to_rhel_entry():
    rhel_env_file = os.path.join(RHEL_EFIDIR_CANONICAL_PATH, 'grubenv')
    rhel_env_file_relpath = os.path.relpath(rhel_env_file, GRUB2_BIOS_ENTRYPOINT)
    run(['ln', '--symbolic', '--force', rhel_env_file_relpath, GRUB2_BIOS_ENV_FILE])


def _copy_file(src_path, dst_path):
    if os.path.exists(dst_path):
        api.current_logger().debug("The {} file already exists and its content will be overwritten.".format(dst_path))

    api.current_logger().info("Copying {} to {}".format(src_path, dst_path))
    try:
        shutil.copy2(src_path, dst_path)
    except (OSError, IOError) as err:
        raise StopActorExecutionError('I/O error({}): {}'.format(err.errno, err.strerror))


def _copy_grub_files(required, optional):
    """
    Copy grub files from redhat/ dir to the /boot/efi/EFI/leapp/ dir.
    """

    all_files = required + optional
    for filename in all_files:
        src_path = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, filename)
        dst_path = os.path.join(RHEL_EFIDIR_CANONICAL_PATH, filename)

        if not os.path.exists(src_path):
            if filename in required:
                msg = 'Required file {} does not exists. Aborting.'.format(filename)
                raise StopActorExecutionError(msg)

            continue

        _copy_file(src_path, dst_path)
