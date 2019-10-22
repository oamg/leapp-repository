from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM


def _get_kernel_rpms():
    rpms = next(api.consume(InstalledRedHatSignedRPM), InstalledRedHatSignedRPM())
    return [pkg for pkg in rpms.items if pkg.name == 'kernel']


def process():
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        return

    pkgs = _get_kernel_rpms()
    if not pkgs:
        # Hypothatical, user is not allowed to install any kernel that is not signed by RH
        # In case we would like to be cautious, we could check whether there are no other
        # kernels installed as well.
        api.current_logger().log.error('Cannot find any installed kernel signed by Red Hat.')
        raise StopActorExecutionError('Cannot find any installed kernel signed by Red Hat.')
    if len(pkgs) > 1:
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
            reporting.Tags([reporting.Tags.KERNEL, reporting.Tags.BOOT]),
            reporting.Flags([reporting.Flags.INHIBITOR]),
            reporting.Remediation(hint=remediation),
            reporting.RelatedResource('package', 'kernel')
        ])
