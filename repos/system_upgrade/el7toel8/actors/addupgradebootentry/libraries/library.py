import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.models import BootContent


def add_boot_entry():
    debug = 'debug' if os.getenv('LEAPP_DEBUG', '0') == '1' else ''

    kernel_dst_path, initram_dst_path = get_boot_file_paths()
    stdlib.call([
        '/usr/sbin/grubby',
        '--add-kernel={0}'.format(kernel_dst_path),
        '--initrd={0}'.format(initram_dst_path),
        '--title=RHEL Upgrade Initramfs',
        '--copy-default',
        '--make-default',
        '--args="{DEBUG} enforcing=0 rd.plymouth=0 plymouth.enable=0"'.format(DEBUG=debug)
    ])


def get_boot_file_paths():
    boot_content_msgs = stdlib.api.consume(BootContent)
    boot_content = next(boot_content_msgs, None)
    if list(boot_content_msgs):
        stdlib.api.current_logger().warning('Unexpectedly received more than one BootContent message.')
    if not boot_content:
        raise StopActorExecutionError('Could not create a GRUB boot entry for the upgrade initramfs',
                                      details={'details': 'Did not receive a message about the leapp-provided'
                                                          'kernel and initramfs'})
    return boot_content.kernel_path, boot_content.initram_path
