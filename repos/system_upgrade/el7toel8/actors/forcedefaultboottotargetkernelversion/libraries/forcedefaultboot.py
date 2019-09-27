import os
from collections import namedtuple

from leapp.libraries import stdlib
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelVersion

KernelInfo = namedtuple('KernelInfo', ('kernel_path', 'initrd_path'))


def get_kernel_info(message):
    kernel_name = 'vmlinuz-{}'.format(message.version)
    initrd_name = 'initramfs-{}.img'.format(message.version)
    kernel_path = os.path.join('/boot', kernel_name)
    initrd_path = os.path.join('/boot', initrd_name)

    target_version_bootable = True
    if not os.path.exists(kernel_path):
        target_version_bootable = False
        api.current_logger().warning('Mandatory kernel %s does not exist', kernel_path)
    if not os.path.exists(initrd_path):
        target_version_bootable = False
        api.current_logger().warning('Mandatory initrd %s does not exist', initrd_path)

    if target_version_bootable:
        return KernelInfo(kernel_path=kernel_path, initrd_path=initrd_path)

    api.current_logger().warning('Skipping check due to missing mandatory files')
    return None


def update_default_kernel(kernel_info):
    try:
        stdlib.run(['grubby', '--info', kernel_info.kernel_path])
    except stdlib.CalledProcessError:
        api.current_logger().error('Expected kernel %s to be installed at the boot loader but cannot be found.',
                                   kernel_info.kernel_path)
    except OSError:
        api.current_logger().error('Could not check for kernel existence in boot loader. Is grubby installed?')
    else:
        try:
            stdlib.run(['grubby', '--set-default', kernel_info.kernel_path])
            stdlib.run(['/usr/sbin/zipl'])
        except (OSError, stdlib.CalledProcessError):
            api.current_logger().error('Failed to set default kernel to: %s', kernel_info.kernel_path, exc_info=True)


def process():
    message = next(api.consume(InstalledTargetKernelVersion), None)
    if not message:
        api.current_logger().warning(('Skipped - Forcing checking and setting default boot entry to target kernel'
                                      ' version due to missing message'))
        return

    try:
        current_default_kernel = stdlib.run(['grubby', '--default-kernel'])['stdout'].strip()
    except (OSError, stdlib.CalledProcessError):
        api.current_logger().warning('Failed to query grubby for default kernel', exc_info=True)
        return

    kernel_info = get_kernel_info(message)
    if not kernel_info:
        return

    if current_default_kernel != kernel_info.kernel_path:
        api.current_logger().warning(('Current default boot entry not target kernel version: Current default: %s.'
                                      'Forcing default kernel to %s'),
                                     current_default_kernel, kernel_info.kernel_path)
        update_default_kernel(kernel_info)
