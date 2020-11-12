from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM


def _normalize_version(version):
    if len(version) != 3:
        if len(version) > 3:
            api.current_logger().debug('Version {} has more than three components, trimming'.format(version))
            del version[3:]
        elif len(version) < 3:
            api.current_logger().debug('Version {} has less than three components, padding'.format(version))
            while len(version) < 3:
                version.append(0)
        api.current_logger().debug('Normalised version to {}'.format(version))
    return version  # could be omitted but it's useful for nesting calls


def get_current_kernel_version():
    """
    Get the version of the running kernel as a tuple of three integers.
    """
    kernel = api.current_actor().configuration.kernel
    return tuple(_normalize_version(list(
        map(int, kernel.split('-')[0].split('.'))
    )))


def get_kernel_rpm_version(rpm):
    """
    Get the version of a kernel RPM as a tuple of three integers.

    :param rpm: An instance of an RPM derived model.
    """
    return tuple(_normalize_version(list(
        map(int, rpm.version.split('.'))
    )))


def get_current_kernel_release():
    """
    Get the release of the running kernel as an integer.
    """
    kernel = api.current_actor().configuration.kernel
    return int(kernel.split('-')[1].split('.')[0])


def get_kernel_rpm_release(rpm):
    """
    Get the release of a kernel RPM as an integer.

    :param rpm: An instance of an RPM derived model.
    """
    return int(rpm.release.split('.')[0])


def get_kernel_rpms():
    """
    Get all installed kernel packages ordered first by version, then release number (ascending).
    """
    rpms = next(api.consume(InstalledRedHatSignedRPM), InstalledRedHatSignedRPM())
    return sorted([pkg for pkg in rpms.items if pkg.name == 'kernel'],
                  key=lambda k: (get_kernel_rpm_version(k), get_kernel_rpm_release(k)))


def process():
    pkgs = get_kernel_rpms()
    if not pkgs:
        # Hypothatical, user is not allowed to install any kernel that is not signed by RH
        # In case we would like to be cautious, we could check whether there are no other
        # kernels installed as well.
        api.current_logger().log.error('Cannot find any installed kernel signed by Red Hat.')
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
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT, reporting.Groups.INHIBITOR]),
            reporting.Remediation(hint=remediation),
            reporting.RelatedResource('package', 'kernel')
        ])

    newest = pkgs[-1]
    newest_release = get_kernel_rpm_release(newest)
    newest_version = get_kernel_rpm_version(newest)
    current_release = get_current_kernel_release()
    current_version = get_current_kernel_version()
    api.current_logger().debug('Current kernel: V {}, R {}'.format(current_version, current_release))
    api.current_logger().debug('Newest kernel: V {}, R {}'.format(newest_version, newest_release))

    if newest_release != current_release or newest_version != current_version:
        title = 'Newest installed kernel not in use'
        summary = ('To ensure a stable upgrade, the machine needs to be'
                   ' booted into the latest installed kernel.')
        remediation = ('Boot into the most up-to-date kernel installed'
                       ' on the machine before running Leapp again.')
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT, reporting.Groups.INHIBITOR]),
            reporting.Remediation(hint=remediation),
            reporting.RelatedResource('package', 'kernel')
        ])
