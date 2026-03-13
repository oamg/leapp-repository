from leapp import reporting
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.common.rpms import has_package
from leapp.models import DistributionSignedRPM


def _report_motif_installed():
    """
    Create report on motif package installation detection.

    Should remind user about present motif package
    installation, warn them about the lack of motif support in RHEL 10, and
    redirect them to online documentation for the migration process.
    """
    summary = (
        'The Motif package has been detected on your system. Motif is no longer'
        ' available in {target_distro} 10. Applications that depend on Motif'
        ' will not work after the upgrade. You will need to either migrate to'
        ' an alternative GUI toolkit (such as GTK or Qt) or maintain the Motif'
        ' package through alternative means.'
    ).format_map(DISTRO_REPORT_NAMES)

    reporting.create_report([
        reporting.Title('Motif has been detected on your system'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(
            title='RHEL 10 Removed Features - Graphics Infrastructures',
            url='https://red.ht/rhel-10-removed-features-graphics-infrastructures'
        ),
        reporting.RelatedResource('package', 'motif'),
        reporting.Remediation(
            hint='Consider migrating applications to a modern GUI toolkit before proceeding with the upgrade.'
        ),
    ])


def report_installed_packages():
    """
    Create reports according to detected motif packages.

    Create the report if the motif rpm (RH signed) is installed.
    """
    has_motif = has_package(DistributionSignedRPM, 'motif')

    if has_motif:
        _report_motif_installed()
