from collections import namedtuple

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.common.config import architecture as arch_config
from leapp.libraries.common.config.version import matches_version
from leapp.libraries.stdlib import api, CalledProcessError, run

KernelPkgInfo = namedtuple('KernelPkgInfo', ('name', 'version', 'release', 'arch', 'nevra'))
KernelPkgNames = namedtuple('KernelPkgNames', ('base', 'core', 'modules'))


class KernelPackageInfoError(StopActorExecutionError):
    """
    Raised when kernel package information cannot be determined.
    """


KERNEL_UNAME_R_PROVIDES = ['kernel-uname-r', 'kernel-rt-uname-r']


class KernelType:
    ORDINARY = 'ordinary'
    REALTIME = 'realtime'


class KernelPageSize:
    PAGE_SIZE_4K = '4k'
    PAGE_SIZE_64K = '64k'


def _normalize_rt64k_suffix(uname_r):
    # TODO(pmocary): Remove when the kernel-rt-64k RPM provides match the actual uname -r output.
    return uname_r.replace('+rt_64k', '+rt-64k')


# TODO: rename rhel_version to something distro agnostic in the new function
# when this is deprecated
def determine_kernel_type_from_uname(rhel_version: str, kernel_uname_r: str) -> str:
    """
    Determine kernel type from given kernel release (uname-r).

    :param rhel_version: Version of RHEL for which the kernel with the uname-r is targeted.
    :type rhel_version: str
    :param kernel_uname_r: Kernel release (uname-r)
    :type kernel_uname_r: str
    :returns: Kernel type based on a given uname_r (values come exclusively from the KernelType class)
    :rtype: str
    """
    if matches_version(['<= 9.2'], rhel_version):
        # NOTE: 64k page size kernel was introduced in 9.2 for aarch64 only. However,
        # the 64k realtime kernel was introduced in 9.6, thus no special infix exists.
        uname_r_infixes = {
            '.rt': KernelType.REALTIME
        }
        for infix, kernel_type in uname_r_infixes.items():
            if infix in kernel_uname_r:
                return kernel_type
    else:
        uname_r_suffixes = {
            '+rt': KernelType.REALTIME,
            '+rt-64k': KernelType.REALTIME,
        }

        kernel_uname_r = _normalize_rt64k_suffix(kernel_uname_r)
        for suffix, kernel_type in uname_r_suffixes.items():
            if kernel_uname_r.endswith(suffix):
                return kernel_type

    return KernelType.ORDINARY


def determine_kernel_page_size() -> str:
    """
    Determine kernel page size for the running kernel using ``getconf PAGE_SIZE``.

    :returns: Kernel page size (values come exclusively from the KernelPageSize class)
    :rtype: str
    """
    try:
        result = run(['getconf', 'PAGE_SIZE'])['stdout'].strip()
        if result == '65536':
            return KernelPageSize.PAGE_SIZE_64K
    except CalledProcessError:
        api.current_logger().warning('Failed to determine kernel page size via getconf, defaulting to 4k.')
    return KernelPageSize.PAGE_SIZE_4K


def get_uname_r_provided_by_kernel_pkg(kernel_pkg_nevra: str, context: mounting.IsolatedActions = None) -> str:
    """
    Get kernel release (uname-r) provided by a given kernel package.

    Calls the ``rpm`` command internally. Returns an empty string if the rpm query fails or no
    matching provide is found.

    :param kernel_pkg_nevra: NEVRA of an installed kernel package
    :type kernel_pkg_nevra: str
    :param context: An isolation context for running commands (e.g. inside a target userspace container).
                    If ``None``, commands run on the host.
    :type context: mounting.IsolatedActions or None
    :returns: uname-r provided by the given package, or empty string on failure
    :rtype: str
    """
    context = context or mounting.NotIsolatedActions(base_dir='/')
    try:
        provides = context.call(['rpm', '-q', '--provides', kernel_pkg_nevra],
                                split=True,
                                callback_raw=lambda fd, value: None,
                                callback_linebuffered=lambda fd, value: None)['stdout']
    except CalledProcessError:
        return ''
    for provide_line in provides:
        if '=' not in provide_line:
            continue
        provide, value = provide_line.split('=', 1)
        provide = provide.strip()
        if provide in KERNEL_UNAME_R_PROVIDES:
            return value.strip()
    return ''


def get_kernel_pkg_info(kernel_pkg_nevra: str) -> KernelPkgInfo:
    """
    Query the RPM database for information about the given kernel package.

    :param kernel_pkg_nevra: NEVRA of an installed kernel package
    :type kernel_pkg_nevra: str
    :returns: Information about the given kernel package
    :rtype: KernelPkgInfo
    :raises KernelPackageInfoError: If the rpm query fails
    """
    query_format = '%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}|'
    try:
        pkg_info = run(['rpm', '-q', '--queryformat', query_format, kernel_pkg_nevra])['stdout'].strip().split('|')
    except CalledProcessError as err:
        raise KernelPackageInfoError(
            message='Unable to obtain kernel package information.',
            details={'Problem': 'Failed to query RPM info for {}: {}'.format(kernel_pkg_nevra, err)})
    return KernelPkgInfo(name=pkg_info[0], version=pkg_info[1], release=pkg_info[2], arch=pkg_info[3],
                         nevra=kernel_pkg_nevra)


def get_kernel_pkg_info_for_uname_r(uname_r: str) -> KernelPkgInfo:
    """
    Identify the kernel package providing a kernel with the given kernel release (uname-r).

    :param uname_r: Kernel release (uname-r)
    :type uname_r: str
    :returns: Information about the kernel package providing given uname_r
    :rtype: KernelPkgInfo
    :raises KernelPackageInfoError: If no package provides given uname_r or if the internal rpm query fails
    """
    kernel_pkg_nevras = []
    for kernel_uname_r_provide in KERNEL_UNAME_R_PROVIDES:
        try:
            kernel_pkg_nevras += run(['rpm', '-q', '--whatprovides', kernel_uname_r_provide], split=True)['stdout']
        except CalledProcessError:  # There is nothing providing a particular provide, e.g, kernel-rt-uname-r
            continue  # Nothing bad happened, continue

    kernel_pkg_nevras = set(kernel_pkg_nevras)

    uname_r = _normalize_rt64k_suffix(uname_r)
    for kernel_pkg_nevra in kernel_pkg_nevras:
        provided_uname = get_uname_r_provided_by_kernel_pkg(kernel_pkg_nevra)  # We know all packages provide a uname
        if not provided_uname:
            api.current_logger().warning('Failed to obtain uname-r provided by %s', kernel_pkg_nevra)
            continue
        provided_uname = _normalize_rt64k_suffix(provided_uname)
        if provided_uname == uname_r:
            return get_kernel_pkg_info(kernel_pkg_nevra)

    raise KernelPackageInfoError(message='Unable to obtain kernel information of the booted kernel: no package is '
                                         'providing the booted kernel release returned by uname.')


def get_target_kernel_pkg_names(kernel_type: str, kernel_page_size: str, arch: str) -> KernelPkgNames:
    """
    Get the base, ``-core``, and ``-modules`` package names for the given kernel variant.

    The ``kernel-64k`` RPM variant only exists on aarch64. On all other architectures the standard
    kernel packages are used regardless of page size.

    :param kernel_type: Type of the kernel
    :type kernel_type: str
    :param kernel_page_size: Page size of the kernel
    :type kernel_page_size: str
    :param arch: System architecture (e.g. ``x86_64``, ``aarch64``, ``ppc64le``)
    :type arch: str
    :returns: Kernel package names
    :rtype: KernelPkgNames
    """
    parts = ['kernel']
    if kernel_type == KernelType.REALTIME:
        parts.append('rt')
    if kernel_page_size == KernelPageSize.PAGE_SIZE_64K and arch == arch_config.ARCH_ARM64:
        parts.append('64k')
    base = '-'.join(parts)
    return KernelPkgNames(base=base, core='{}-core'.format(base), modules='{}-modules'.format(base))
