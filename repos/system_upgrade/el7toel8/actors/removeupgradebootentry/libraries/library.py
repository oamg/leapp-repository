from subprocess import CalledProcessError

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, call
from leapp.models import BootContent


def remove_boot_entry():
    # we need to make sure /boot is mounted before trying to remove the boot entry
    try:
        call([
            '/bin/mount', '/boot'
        ])
    except CalledProcessError:
        # /boot has been most likely already mounted
        pass
    kernel_filepath = get_upgrade_kernel_filepath()
    call([
        '/usr/sbin/grubby',
        '--remove-kernel={0}'.format(kernel_filepath)
    ])
    # TODO: Move calling `mount -a` to a separate actor as it is not really related to removing the upgrade boot entry.
    #       It's worth to call it after removing the boot entry to avoid boot loop in case mounting fails.
    call([
        '/bin/mount', '-a'
    ])


def get_upgrade_kernel_filepath():
    boot_content_msgs = api.consume(BootContent)
    boot_content = next(boot_content_msgs, None)
    if list(boot_content_msgs):
        api.current_logger().warning('Unexpectedly received more than one BootContent message.')
    if not boot_content:
        raise StopActorExecutionError('Could not create a GRUB boot entry for the upgrade initramfs',
                                      details={'details': 'Did not receive a message about the leapp-provided'
                                                          'kernel and initramfs'})
    return boot_content.kernel_path
