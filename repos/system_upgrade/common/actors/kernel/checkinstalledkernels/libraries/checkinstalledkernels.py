try:
    from rpm import labelCompare
except ImportError:
    # this can happen only on non-rpm based systems or with Python3 on RHEL 7
    # based OSs, as the rpm python module is available here just for Python2
    # - and vice versa on F31+
    # This will not happen in real run, just in case of unit-tests..
    def labelCompare(*args):
        raise NotImplementedError(
            "The labelCompare function is not implemented for the python"
            " you are using."
        )

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture, version
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM


def get_current_kernel_version():
    """
    Get the version of the running kernel as a string.
    """
    return api.current_actor().configuration.kernel.split('-')[0]


def get_current_kernel_release():
    """
    Get the release of the current kernel as a string.
    """
    return api.current_actor().configuration.kernel.split('-')[1]


def get_current_kernel_evr():
    """
    Get a 3-tuple (EVR) of the current booted kernel.

    Epoch in this case is always empty string. In case of kernel, epoch is
    never expected to be set.
    """
    return ('', get_current_kernel_version(), get_current_kernel_release())


def get_pkgs(pkg_name):
    """
    Get all installed packages of the given name signed by Red Hat.
    """
    rpms = next(api.consume(InstalledRedHatSignedRPM), InstalledRedHatSignedRPM()).items
    return [pkg for pkg in rpms if pkg.name == pkg_name]


def get_EVR(pkg):
    """
    Return 3-tuple EVR (_epoch_, version, release) of the given RPM.

    Epoch is always set as an empty string as in case of kernel epoch is not
    expected to be set - ever.

    The release includes an architecture as well.
    """
    return ('', pkg.version, '{}.{}'.format(pkg.release, pkg.arch))


def _get_pkgs_evr(pkgs):
    """
    Return 3-tuples (EVR) of the given packages.
    """
    return [get_EVR(pkg) for pkg in pkgs]


def get_newest_evr(pkgs):
    """
    Return the 3-tuple (EVR) of the newest package from the given list.

    Return None if the given list is empty. It's expected that all given
    packages have same name.
    """
    if not pkgs:
        return None
    rpms_evr = _get_pkgs_evr(pkgs)

    newest_evr = rpms_evr.pop()
    for pkg in rpms_evr:
        if labelCompare(newest_evr, pkg) < 0:
            newest_evr = pkg
    return newest_evr


def _get_kernel_rpm_name():
    base_name = 'kernel'
    if version.is_rhel_realtime():
        api.current_logger().info('The Real Time kernel boot detected.')
        base_name = 'kernel-rt'

    if version.get_source_major_version() == '7':
        return base_name

    # Since RHEL 8, the kernel|kernel-rt rpm is just a metapackage that even
    # does not have to be installed on the system.
    # The kernel-core|kernel-rt-core rpm is the one we care about instead.
    return '{}-core'.format(base_name)


def process():
    kernel_name = _get_kernel_rpm_name()
    pkgs = get_pkgs(kernel_name)
    if not pkgs:
        # Hypothatical, user is not allowed to install any kernel that is not signed by RH
        # In case we would like to be cautious, we could check whether there are no other
        # kernels installed as well.
        api.current_logger().error('Cannot find any installed kernel signed by Red Hat.')
        raise StopActorExecutionError('Cannot find any installed kernel signed by Red Hat.')

    if len(pkgs) > 1 and architecture.matches_architecture(architecture.ARCH_S390X):
        # It's temporary solution, so no need to try automatize everything.
        title = 'Multiple kernels installed'
        summary = ('The upgrade process does not handle well the case when multiple kernels'
                   ' are installed on s390x. There is a severe risk of the bootloader configuration'
                   ' getting corrupted during the upgrade.')
        remediation = ('Boot into the most up-to-date kernel and remove all older'
                       ' kernels installed on the machine before running Leapp again.')
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Remediation(hint=remediation),
            reporting.RelatedResource('package', 'kernel')
        ])

    current_evr = get_current_kernel_evr()
    newest_evr = get_newest_evr(pkgs)

    api.current_logger().debug('Current kernel EVR: {}'.format(current_evr))
    api.current_logger().debug('Newest kernel EVR: {}'.format(newest_evr))

    if current_evr != newest_evr:
        title = 'Newest installed kernel not in use'
        summary = ('To ensure a stable upgrade, the machine needs to be'
                   ' booted into the latest installed kernel.')
        remediation = ('Boot into the most up-to-date kernel installed'
                       ' on the machine before running Leapp again.')
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Remediation(hint=remediation),
            reporting.RelatedResource('package', 'kernel')
        ])
