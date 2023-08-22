import os
from collections import namedtuple

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import kernel as kernel_lib
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import InstalledTargetKernelInfo, InstalledTargetKernelVersion, KernelInfo
from leapp.utils.deprecation import suppress_deprecation

KernelBootFiles = namedtuple('KernelBootFiles', ('vmlinuz_path', 'initramfs_path'))


def get_kernel_pkg_name(rhel_major_version, kernel_type):
    """
    Get the name of the package providing kernel binaries.

    :param str rhel_major_version: RHEL major version
    :param KernelType kernel_type: Type of the kernel
    :returns: Kernel package name
    :rtype: str
    """
    if rhel_major_version == '7':
        kernel_pkg_name_table = {
            kernel_lib.KernelType.ORDINARY: 'kernel',
            kernel_lib.KernelType.REALTIME: 'kernel-rt'
        }
    else:
        kernel_pkg_name_table = {
            kernel_lib.KernelType.ORDINARY: 'kernel-core',
            kernel_lib.KernelType.REALTIME: 'kernel-rt-core'
        }
    return kernel_pkg_name_table[kernel_type]


def get_target_kernel_package_nevra(kernel_pkg_name):
    try:
        kernel_nevras = run(['rpm', '-q', kernel_pkg_name], split=True)['stdout']
    except CalledProcessError:
        return ''

    target_kernel_el = 'el{}'.format(get_target_major_version())
    for kernel_nevra in kernel_nevras:
        if target_kernel_el in kernel_nevra:
            return kernel_nevra
    return ''


def get_boot_files_provided_by_kernel_pkg(kernel_nevra):
    initramfs_path = ''
    vmlinuz_path = ''
    err_msg = 'Cannot determine location of the target kernel boot image and corresponding initramfs .'
    try:
        kernel_pkg_files = run(['rpm', '-q', '-l', kernel_nevra], split=True)['stdout']
        for kernel_file_path in kernel_pkg_files:
            dirname = os.path.dirname(kernel_file_path)
            if dirname != '/boot':
                continue
            basename = os.path.basename(kernel_file_path)
            if basename.startswith('vmlinuz'):
                vmlinuz_path = kernel_file_path
            elif basename.startswith('initramfs'):
                initramfs_path = kernel_file_path
    except CalledProcessError:
        raise StopActorExecutionError(err_msg)
    if not vmlinuz_path or not initramfs_path:
        raise StopActorExecutionError(err_msg)
    return KernelBootFiles(vmlinuz_path=vmlinuz_path, initramfs_path=initramfs_path)


@suppress_deprecation(InstalledTargetKernelVersion)
def process():
    # pylint: disable=no-else-return  - false positive
    # TODO: should we take care about stuff of kernel-rt and kernel in the same
    # time when both are present? or just one? currently, handle only one
    # of these during the upgrade. kernel-rt has higher prio when original sys
    # was realtime
    src_kernel_info = next(api.consume(KernelInfo), None)
    if not src_kernel_info:
        return  # Will not happen, other actors would inhibit the upgrade

    target_ver = get_target_major_version()
    target_kernel_pkg_name = get_kernel_pkg_name(target_ver, src_kernel_info.type)
    target_kernel_nevra = get_target_kernel_package_nevra(target_kernel_pkg_name)

    if src_kernel_info.type != kernel_lib.KernelType.ORDINARY and not target_kernel_nevra:
        api.current_logger().warning('The kernel-rt-core rpm from the target RHEL has not been detected. Switching '
                                     'to non-preemptive kernel.')
        target_kernel_pkg_name = get_kernel_pkg_name(target_ver, kernel_lib.KernelType.ORDINARY)
        target_kernel_nevra = get_target_kernel_package_nevra(target_kernel_pkg_name)

    if target_kernel_nevra:
        boot_files = get_boot_files_provided_by_kernel_pkg(target_kernel_nevra)
        target_kernel_version = kernel_lib.get_uname_r_provided_by_kernel_pkg(target_kernel_nevra)
        installed_kernel_info = InstalledTargetKernelInfo(pkg_nevra=target_kernel_nevra,
                                                          uname_r=target_kernel_version,
                                                          kernel_img_path=boot_files.vmlinuz_path,
                                                          initramfs_path=boot_files.initramfs_path)

        api.produce(installed_kernel_info)

        # Backwards compatibility
        # Expects that the kernel nevra has the following format: <pkg_name>-<version>-<release>.<arch>
        version = '-'.join(target_kernel_nevra.split('-')[-2:])  # (-2)-th is <version>; take <version>-<release>...
        api.produce(InstalledTargetKernelVersion(version=version))
    else:
        # This is not expected, however, we are past the point that raising an exception would do any good.
        # It is better to finish the upgrade with 80% things done rather than falling into emergency mode
        api.current_logger().warning('Failed to identify package providing the target kernel.')
        pass
