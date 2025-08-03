import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import DefaultSourceBootEntry


def extract_path_with_img_extension(initramfs_path):
    try:
        img_extension_start = initramfs_path.rindex('.img')  # .index() returns the starting position
        initramfs_path = initramfs_path[:img_extension_start + len('.img')]

        if not os.path.exists(initramfs_path):
            msg = 'Failed to extract the path to the default\'s boot entry initramfs.'
            details = {'details': f'The current initramfs path {initramfs_path}'}
            raise StopActorExecutionError(msg, details=details)

    except ValueError:
        details = {'details': f'The current initramfs path {initramfs_path}'}
        # The system is using some non-traditional naming scheme, no point in trying to extract image path
        # Better safe, than sorry, we stop the upgrade here rather than crashing because of a weird path
        msg = ('The initrd path of the default kernel does not contain the `.img` extension, '
               'thus the upgrade cannot safely continue.')
        raise StopActorExecutionError(msg, details=details)
    return initramfs_path


def scan_default_source_boot_entry():
    try:
        default_kernel = run(['grubby', '--default-kernel'])['stdout'].strip()
        default_kernel_info_lines = run(['grubby', '--info', default_kernel], split=True)['stdout']

    except CalledProcessError as err:
        details = {'details': str(err)}
        raise StopActorExecutionError('Failed to determine default boot entry.', details=details)

    # Note that there can be multiple entries listed sharing the same default kernel.
    # The parsing is done in a way that it should not fail in such a case. For the current use
    # it does not matter -- at the moment we care primarily about the initramfs path, and these
    # entries should typically share the initramfs.

    default_kernel_info = {}
    for line in default_kernel_info_lines:
        key, value = line.split('=', 1)
        default_kernel_info[key] = value.strip('"')

    initramfs_path = default_kernel_info['initrd']
    initramfs_path = extract_path_with_img_extension(initramfs_path)

    default_boot_entry_message = DefaultSourceBootEntry(
        initramfs_path=initramfs_path,
        kernel_path=default_kernel_info['kernel'],
    )

    api.produce(default_boot_entry_message)
