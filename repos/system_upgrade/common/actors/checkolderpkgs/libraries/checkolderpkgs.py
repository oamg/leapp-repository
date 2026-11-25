import re

from leapp import reporting
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM


def process():
    """
    Main processing function to detect distribution-signed packages from older releases.
    """
    older_packages = _get_older_release_packages()

    if older_packages:
        _inhibit_upgrade(older_packages)
        return

    api.current_logger().debug('No distribution-signed packages from older releases detected.')


def _get_older_release_packages():
    """
    Scan distribution-signed RPMs and return packages from older releases.

    Returns:
        list: List of tuples (package_name, release_string) for packages
              from older releases.
    """
    source_version = get_source_major_version()
    api.current_logger().debug(
        'Scanning for distribution-signed packages from releases older than EL{}'.format(source_version)
    )

    older_packages = []

    for rpm_msg in api.consume(DistributionSignedRPM):
        for rpm in rpm_msg.items:
            if _is_older_release(rpm.release, source_version):
                api.current_logger().debug(
                    'Found older release package: {} (release: {})'.format(
                        rpm.name, rpm.release
                    )
                )
                older_packages.append((rpm.name, rpm.release))

    return older_packages


def _is_older_release(release_string, current_version):
    """
    Check if a package release string indicates an older release.

    Args:
        release_string (str): The RPM release field (e.g., "1.el7", "2.el9_4")
        current_version (str): Current major version (e.g., "9")

    Returns:
        bool: True if the package is from an older release, False otherwise.
    """
    if not release_string:
        return False

    # Match .elX or .elX_ patterns in the release string
    # Examples: .el6, .el7, .el8, .el9_4, .el10
    match = re.search(r'\.el(\d+)(?:_|$|\.|[^0-9])', release_string)
    if not match:
        return False

    release_version = match.group(1)
    current_ver_int = int(current_version)
    release_ver_int = int(release_version)

    # Package is from an older release if its version is less than current
    # (e.g., .el7 or .el8 on EL 9)
    return release_ver_int < current_ver_int


def _inhibit_upgrade(older_packages):
    """
    Create an inhibitor report for detected older release packages.

    Args:
        older_packages (list): List of tuples (package_name, release_string)
    """
    # Limit displayed packages to first 20 to avoid overly long reports
    max_display = 20
    package_list = [
        '- {} (release: {})'.format(name, release)
        for name, release in older_packages[:max_display]
    ]

    if len(older_packages) > max_display:
        package_list.append(
            '... and {} more packages'.format(len(older_packages) - max_display)
        )

    title = 'Distribution-signed packages from different releases detected'
    summary = (
        'The system contains {} distribution-signed package(s) from older releases:\n\n{}\n\n'
        'These packages may cause system instability, upgrade failures, or result in '
        'unsupported configurations after the upgrade.'
        .format(len(older_packages), '\n'.join(package_list))
    )

    remediation_hint = (
        'Before proceeding with the upgrade, remove the affected distribution-signed packages '
        'using "dnf remove <package-name>". If any of these packages are still needed after the '
        'upgrade, they should be installed from repositories for the target system version.'
    )

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Remediation(hint=remediation_hint),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.RelatedResource('package', 'rpm'),
    ])
