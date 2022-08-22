import os

from leapp.exceptions import StopActorExecution
from leapp.libraries.stdlib import api
from leapp.models import BootContent


def remove_boot_files():
    boot_content_msgs = api.consume(BootContent)
    boot_content = next(boot_content_msgs, None)
    if list(boot_content_msgs):
        api.current_logger().warning('Unexpectedly received more than one BootContent message.')
    if not boot_content:
        api.current_logger().warning('Did not receive a message about the leapp-provided kernel and initramfs ->'
                                     ' Skipping removal of these files.')
        raise StopActorExecution
    for filepath in boot_content.kernel_path, boot_content.initram_path:
        remove_file(filepath)


def remove_file(filepath):
    try:
        os.remove(filepath)
    except OSError as err:
        api.current_logger().error('Could not remove {0}: {1}.'.format(filepath, err))
