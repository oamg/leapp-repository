from collections import namedtuple

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run

KernelPkgInfo = namedtuple('KernelPkgInfo', ('name', 'version', 'release', 'arch', 'nevra'))


KERNEL_UNAME_R_PROVIDES = ['kernel-uname-r', 'kernel-rt-uname-r']


class KernelType(object):
    ORDINARY = 'ordinary'
    REALTIME = 'realtime'


def determine_kernel_type_from_uname(rhel_version, kernel_uname_r):
    """
    Determine kernel type from given kernel release (uname-r).

    :param str rhel_version: Version of RHEL for which the kernel with the uname-r is targeted.
    :param str kernel_uname_r: Kernel release (uname-r)
    :returns: Kernel type based on a given uname_r
    :rtype: KernelType
    """
    version_fragments = rhel_version.split('.')
    major_ver = version_fragments[0]
    minor_ver = version_fragments[1] if len(version_fragments) > 1 else '0'
    rhel_version = (major_ver, minor_ver)

    if rhel_version <= ('9', '2'):
        uname_r_infixes = {
            '.rt': KernelType.REALTIME
        }
        for infix, kernel_type in uname_r_infixes.items():
            if infix in kernel_uname_r:
                return kernel_type
    else:
        uname_r_suffixes = {
            '+rt': KernelType.REALTIME
        }

        for suffix, kernel_type in uname_r_suffixes.items():
            if kernel_uname_r.endswith(suffix):
                return kernel_type

    return KernelType.ORDINARY


def get_uname_r_provided_by_kernel_pkg(kernel_pkg_nevra):
    """
    Get kernel release (uname-r) provided by a given kernel package.

    Calls the ``rpm`` command internally and might raise CalledProcessError if the rpm query fails.

    :param str kernel_pkg_nevra: NEVRA of an installed kernel package
    :returns: uname-r provided by the given package
    :rtype: str
    """
    provides = run(['rpm', '-q', '--provides', kernel_pkg_nevra],
                   split=True,
                   callback_raw=lambda fd, value: None,
                   callback_linebuffered=lambda fd, value: None)['stdout']
    for provide_line in provides:
        if '=' not in provide_line:
            continue
        provide, value = provide_line.split('=', 1)
        provide = provide.strip()
        if provide in KERNEL_UNAME_R_PROVIDES:
            return value.strip()
    return ''


def get_kernel_pkg_info(kernel_pkg_nevra):
    """
    Query the RPM database for information about the given kernel package.

    Calls the ``rpm`` command internally and might raise CalledProcessError if the rpm query fails.

    :param str kernel_pkg_nevra: NEVRA of an installed kernel package
    :returns: Information about the given kernel package
    :rtype: KernelPkgInfo
    """
    query_format = '%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}|'
    pkg_info = run(['rpm', '-q', '--queryformat', query_format, kernel_pkg_nevra])['stdout'].strip().split('|')
    return KernelPkgInfo(name=pkg_info[0], version=pkg_info[1], release=pkg_info[2], arch=pkg_info[3],
                         nevra=kernel_pkg_nevra)


def get_kernel_pkg_info_for_uname_r(uname_r):
    """
    Identify the kernel package providing a kernel with the given kernel release (uname-r).

    Raises ``StopActorExecutionError`` if no package provides given uname_r or if the internal rpm query fails.
    :param str uname_r: NEVRA of an installed kernel package
    :returns: Information about the kernel package providing given uname_r
    :rtype: KernelPkgInfo
    """
    kernel_pkg_nevras = []
    for kernel_uname_r_provide in KERNEL_UNAME_R_PROVIDES:
        try:
            kernel_pkg_nevras += run(['rpm', '-q', '--whatprovides', kernel_uname_r_provide], split=True)['stdout']
        except CalledProcessError:  # There is nothing providing a particular provide, e.g, kernel-rt-uname-r
            continue  # Nothing bad happened, continue

    kernel_pkg_nevras = set(kernel_pkg_nevras)

    for kernel_pkg_nevra in kernel_pkg_nevras:
        provided_uname = get_uname_r_provided_by_kernel_pkg(kernel_pkg_nevra)  # We know all packages provide a uname
        if not provided_uname:
            api.current_logger().warning('Failed to obtain uname-r provided by %s', kernel_pkg_nevra)
        if provided_uname == uname_r:
            return get_kernel_pkg_info(kernel_pkg_nevra)

    raise StopActorExecutionError(message='Unable to obtain kernel information of the booted kernel: no package is '
                                          'providing the booted kernel release returned by uname.')
