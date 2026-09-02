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
from leapp.libraries.common.config import architecture, is_conversion, utils
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, KernelInfo


def get_all_pkgs_with_name(pkg_name):
    """
    Get all installed packages of the given name signed by Red Hat.
    """
    rpms = next(api.consume(DistributionSignedRPM), DistributionSignedRPM()).items
    return [pkg for pkg in rpms if pkg.name == pkg_name]


def get_EVR(pkg):
    """
    Return 3-tuple EVR (_epoch_, version, release) of the given RPM.

    Epoch is always set as an empty string as in case of kernel epoch is not
    expected to be set - ever.
    """
    return ('', pkg.version, pkg.release)


def get_newest_evr(pkgs):
    """
    Return the 3-tuple (EVR) of the newest package from the given list.

    Return None if the given list is empty. It's expected that all given
    packages have same name.
    """
    if not pkgs:
        return None

    newest_evr = get_EVR(pkgs[0])
    for pkg in pkgs:
        evr = get_EVR(pkg)
        if labelCompare(newest_evr, evr) < 0:
            newest_evr = evr

    return newest_evr


def _is_conversion_with_uek(kernel_info):
    """Check if this is a conversion and the system is booted into UEK."""
    # TODO: Replace uname_r string check with kernel_info.type once UEK is modeled as a KernelType
    return is_conversion() and 'uek' in kernel_info.uname_r


def process():
    kernel_info = utils._require_exactly_one_message_of_type(KernelInfo)

    if _is_conversion_with_uek(kernel_info):
        reporting.create_report([
            reporting.Title('Unbreakable Enterprise Kernel (UEK) is currently in use'),
            reporting.Summary(
                'The system is currently booted into the Unbreakable Enterprise Kernel (UEK).'
                ' The in-place upgrade and conversion are not supported with UEK.'
                ' The system must be booted into the Red Hat Compatible Kernel (RHCK)'
                ' before the upgrade and conversion can proceed.'
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Remediation(
                hint=(
                    'To proceed with the upgrade and conversion, boot into the Red Hat Compatible'
                    ' Kernel (RHCK). Ensure that the kernel package is installed, set the Red Hat'
                    ' Compatible Kernel (RHCK) as the default boot kernel, reboot the system.'
                )
            ),
        ])
        return

    pkgs = get_all_pkgs_with_name(kernel_info.pkg.name)

    if not pkgs:
        # Hypothetical, user is not allowed to install any kernel that is not signed by RH
        # In case we would like to be cautious, we could check whether there are no other
        # kernels installed as well.
        api.current_logger().error('Cannot find any installed kernel signed by Red Hat.')
        raise StopActorExecutionError('Cannot find any installed kernel signed by Red Hat.')

    if len(pkgs) > 1 and architecture.matches_architecture(architecture.ARCH_S390X):
        # It's temporary solution, so no need to try automate everything.
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

    current_kernel_evr = get_EVR(kernel_info.pkg)
    newest_kernel_evr = get_newest_evr(pkgs)

    api.current_logger().debug('Current kernel EVR: {}'.format(current_kernel_evr))
    api.current_logger().debug('Newest kernel EVR: {}'.format(newest_kernel_evr))

    if current_kernel_evr != newest_kernel_evr:
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
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/7014134',
                title='Leapp upgrade fail with error "Inhibitor:Newest installed kernel '
                      'not in use" Upgrade cannot proceed'
            ),
            reporting.RelatedResource('package', 'kernel')
        ])
