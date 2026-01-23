from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.models import DistributionSignedRPM

# List of Xorg server packages to check
_XORG_PACKAGES = [
    'xorg-x11-server-Xdmx',
    'xorg-x11-server-Xephyr',
    'xorg-x11-server-Xnest',
    'xorg-x11-server-Xorg',
    'xorg-x11-server-Xvfb',
]

# Summary for Xorg report
_report_xorg_inst_summary = (
    'Xorg server packages have been detected on your system. The Xorg server is no longer available '
    'in RHEL 10. Applications and services that depend on Xorg server packages will not work '
    'after the upgrade. Migrate to Wayland or maintain the Xorg packages through '
    'alternative means. The following Xorg server packages have been detected and are not available in RHEL 10:{}{}'.format(FMT_LIST_SEPARATOR, FMT_LIST_SEPARATOR.join(<the packages>))
)

_report_xorg_inst_hint = (
    'Consider migrating to Wayland before proceeding with the upgrade.'
)

# Link URL for Xorg report
_report_xorg_inst_link_url = 'https://red.ht/rhel-10-removed-features-graphics-infrastructures'


def _report_xorg_installed(packages):
    """
    Create report on Xorg server package installation detection.

    Should remind user about present Xorg server package installations,
    warn them about the lack of Xorg support in RHEL 10, and redirect
    them to online documentation for the migration process.

    :param packages: List of installed Xorg package names
    :type packages: list
    """
    reporting.create_report([
        reporting.Title('Xorg server packages have been detected on your system'),
        reporting.Summary(_report_xorg_inst_summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='RHEL 10 Removed Features - Graphics Infrastructures',
                               url=_report_xorg_inst_link_url),
        reporting.Remediation(hint=_report_xorg_inst_hint),
        ] + [reporting.RelatedResource('package', pkg) for pkg in packages])


def report_installed_packages():
    """
    Create reports according to detected Xorg server packages.

    Create the report if any Xorg server rpm (RH signed) is installed.
    """
    installed_packages = []

    for package in _XORG_PACKAGES:
        if has_package(DistributionSignedRPM, package):
            installed_packages.append(package)

    if installed_packages:
        _report_xorg_installed(installed_packages)
