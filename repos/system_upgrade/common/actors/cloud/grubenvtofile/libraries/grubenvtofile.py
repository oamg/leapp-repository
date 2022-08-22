from leapp.libraries.stdlib import api, CalledProcessError, run

BIOS_PATH = '/boot/grub2/grubenv'
EFI_PATH = '/boot/efi/EFI/redhat/grubenv'


def grubenv_to_file():
    try:
        run(['unlink', BIOS_PATH])
    except CalledProcessError as err:
        api.current_logger().warning('Could not unlink {}: {}'.format(BIOS_PATH, str(err)))
        return
    try:
        run(['cp', '-a', EFI_PATH, BIOS_PATH])
        api.current_logger().info(
            '{} converted from being a symlink pointing to {} file into a regular file'.format(BIOS_PATH, EFI_PATH)
        )
    except CalledProcessError as err:
        api.current_logger().warning('Could not copy content of {} to {}: {}'.format(EFI_PATH, BIOS_PATH, str(err)))
