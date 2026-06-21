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


# Deprecated: KERNEL_UNAME_R_PROVIDES is no longer used.
KERNEL_UNAME_R_PROVIDES = ['kernel-uname-r', 'kernel-rt-uname-r']


class KernelType:
    ORDINARY = 'ordinary'
    REALTIME = 'realtime'


class KernelPageSize:
    PAGE_SIZE_4K = '4k'
    PAGE_SIZE_64K = '64k'


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

    Extracts the kernel version from the package's ``/lib/modules/<version>`` file paths.
    Returns an empty string if the rpm query fails or no matching path is found.

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
        file_list = context.call(['rpm', '-q', '-l', kernel_pkg_nevra],
                                 split=True,
                                 callback_raw=lambda fd, value: None,
                                 callback_linebuffered=lambda fd, value: None)['stdout']
    except CalledProcessError:
        return ''
    modules_prefix = '/lib/modules/'
    for file_path in file_list:
        if not file_path.startswith(modules_prefix):
            continue
        # Strip the /lib/modules/ prefix and take the first path component (the kernel version)
        version = file_path[len(modules_prefix):].split('/', 1)[0]
        if version:
            return version
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

    Queries RPM for packages owning ``/lib/modules/<uname_r>`` and returns info about the ``-core``
    kernel package among the results.

    :param uname_r: Kernel release (uname-r)
    :type uname_r: str
    :returns: Information about the kernel package providing given uname_r
    :rtype: KernelPkgInfo
    :raises KernelPackageInfoError: If no package provides given uname_r or if the internal rpm query fails
    """
    try:
        pkg_nevras = run(['rpm', '-q', '--whatprovides', '/lib/modules/{}'.format(uname_r)],
                         split=True)['stdout']
    except CalledProcessError as err:
        raise KernelPackageInfoError(
            message='Unable to obtain kernel information of the booted kernel.',
            details={'Problem': 'No package owns /lib/modules/{}: {}'.format(uname_r, err)})

    for pkg_nevra in pkg_nevras:
        # Skip packages that are clearly not kernel core packages to avoid unnecessary rpm queries
        if '-core' not in pkg_nevra or '-modules' in pkg_nevra:
            continue
        pkg_info = get_kernel_pkg_info(pkg_nevra)
        if pkg_info.name.endswith('-core'):
            return pkg_info

    raise KernelPackageInfoError(
        message='Unable to obtain kernel information of the booted kernel.',
        details={'Problem': 'No installed package owning /lib/modules/{} is a kernel core package.'.format(uname_r)})


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
