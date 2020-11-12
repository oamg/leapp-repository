from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM


def get_kernel_rpm_release(rpm):
    """
    Get the release of a kernel RPM as an integer.

    :param rpm: An instance of an RPM derived model.
    """
    return int(rpm.release.split('.')[0])


def get_kernel_debug_rpms():
    """
    Get all installed kernel-debug packages ordered by release number (ascending).
    """
    rpms = next(api.consume(InstalledRedHatSignedRPM), InstalledRedHatSignedRPM())
    return sorted([pkg for pkg in rpms.items if pkg.name == 'kernel-debug'], key=get_kernel_rpm_release)


def process():
    pkgs = get_kernel_debug_rpms()
    if len(pkgs) > 1:
        title = 'Multiple debug kernels installed'
        summary = ('DNF cannot produce a valid upgrade transaction when'
                   ' multiple kernel-debug packages are installed.')
        hint = ('Remove all but one kernel-debug packages before running Leapp again.')
        all_but_latest_kernel_debug = pkgs[:-1]
        packages = ['{n}-{v}-{r}'.format(n=pkg.name, v=pkg.version, r=pkg.release)
                    for pkg in all_but_latest_kernel_debug]
        commands = [['yum', '-y', 'remove'] + packages]
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.INHIBITOR]),
            reporting.Remediation(hint=hint, commands=commands),
            reporting.RelatedResource('package', 'kernel-debug')
        ])
