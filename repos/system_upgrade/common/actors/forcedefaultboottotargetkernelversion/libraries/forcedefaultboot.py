from leapp.libraries import stdlib
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api, config
from leapp.models import InstalledTargetKernelInfo


def update_default_kernel(kernel_info):
    try:
        stdlib.run(['grubby', '--info', kernel_info.kernel_img_path])
    except stdlib.CalledProcessError:
        api.current_logger().error('Expected kernel %s to be installed at the boot loader but cannot be found.',
                                   kernel_info.kernel_img_path)
    except OSError:
        api.current_logger().error('Could not check for kernel existence in boot loader. Is grubby installed?')
    else:
        try:
            stdlib.run(['grubby', '--set-default', kernel_info.kernel_img_path])
            if architecture.matches_architecture(architecture.ARCH_S390X):
                # on s390x we need to call zipl explicitly because of issue in grubby,
                # otherwise the new boot entry will not be set as default
                # See https://bugzilla.redhat.com/show_bug.cgi?id=1764306
                stdlib.run(['/usr/sbin/zipl'])
        except (OSError, stdlib.CalledProcessError):
            api.current_logger().error('Failed to set default kernel to: %s',
                                       kernel_info.kernel_img_path, exc_info=True)


def process():
    is_system_s390x = architecture.matches_architecture(architecture.ARCH_S390X)
    if config.is_debug and not is_system_s390x:  # pylint: disable=using-constant-test
        try:
            # the following command prints output of grubenv for debugging purposes and is repeated after setting
            # default kernel so we can be sure we have the right saved entry
            #
            # saved_entry=63...
            # kernelopts=root=/dev/mapper...
            #
            #
            # boot_success and boot_indeterminate parameters are added later by one-shot systemd service
            stdlib.run(['grub2-editenv', 'list'])
        except stdlib.CalledProcessError:
            api.current_logger().error('Failed to execute "grub2-editenv list" command')

    kernel_info = next(api.consume(InstalledTargetKernelInfo), None)
    if not kernel_info:
        api.current_logger().warning(('Skipped - Forcing checking and setting default boot entry to target kernel'
                                      ' version due to missing message'))
        return

    if not kernel_info.kernel_img_path:  # Should be always set
        api.current_logger().warning(('Skipping forcing of default boot entry - target kernel info '
                                      'does not contain a kernel image path.'))
        return

    try:
        current_default_kernel = stdlib.run(['grubby', '--default-kernel'])['stdout'].strip()
    except (OSError, stdlib.CalledProcessError):
        api.current_logger().warning('Failed to query grubby for default kernel', exc_info=True)
        return

    for type_ in ('index', 'title'):
        try:
            stdlib.run(['grubby', '--default-{}'.format(type_)])
        except (OSError, stdlib.CalledProcessError):
            api.current_logger().warning('Failed to query grubby for default {}'.format(type_), exc_info=True)
            return

    if current_default_kernel != kernel_info.kernel_img_path:
        api.current_logger().warning(('Current default boot entry not target kernel version: Current default: %s.'
                                      'Forcing default kernel to %s'),
                                     current_default_kernel, kernel_info.kernel_img_path)
        update_default_kernel(kernel_info)
    if config.is_debug and not is_system_s390x:  # pylint: disable=using-constant-test
        try:
            stdlib.run(['grub2-editenv', 'list'])
        except stdlib.CalledProcessError:
            api.current_logger().error('Failed to execute "grub2-editenv list" command')
