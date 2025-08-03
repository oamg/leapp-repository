from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import DefaultSourceBootEntry


def scan_default_source_boot_entry():
    try:
        default_kernel = run(['grubby', '--default-kernel'])['stdout'].strip()
        default_kernel_info_lines = run(['grubby', '--info', default_kernel], split=True)['stdout']

    except CalledProcessError as err:
        details = {'error': str(err)}  # @REVIEW: Is there some guidance on how to fill 'details'?
        raise StopActorExecutionError('Failed to determine default boot entry.', details=details)

    default_kernel_info = {}
    for line in default_kernel_info_lines:
        key, value = line.split('=', 1)
        default_kernel_info[key] = value.strip('"')

    default_boot_entry_message = DefaultSourceBootEntry(
        initramfs_path=default_kernel_info['initrd'],
        kernel_path=default_kernel_info['kernel'],
    )

    api.produce(default_boot_entry_message)
