import re

from leapp import reporting
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM


def process():
    """
    Main processing function to detect packages from older RHEL releases.
    """
    older_packages = _get_older_release_packages()

    if older_packages:
        _inhibit_upgrade(older_packages)
        return

    api.current_logger().debug('No packages from older RHEL releases detected.')


def _get_older_release_packages():
    """
    Scan installed RPMs and return packages from older RHEL releases.

    Returns:
        list: List of tuples (package_name, release_string) for packages
              from older releases.
    """
    source_version = get_source_major_version()
    api.current_logger().debug(
        'Scanning for packages from releases older than RHEL {}'.format(source_version)
    )

    older_packages = []

    for rpm_msg in api.consume(InstalledRPM):
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
    Check if a package release string indicates an older RHEL release.

    Args:
        release_string (str): The RPM release field (e.g., "1.el7", "2.el9_4")
        current_version (str): Current RHEL major version (e.g., "9")

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
    # (e.g., .el7 or .el8 on RHEL 9)
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

    title = 'Packages from different RHEL releases detected'
    summary = (
        'The system contains {} package(s) from older RHEL releases:\n\n{}\n\n'
        'These packages may cause system instability, upgrade failures, or result in '
        'unsupported configurations. Red Hat does not support systems with packages '
        'from different major RHEL releases.'
        .format(len(older_packages), '\n'.join(package_list))
    )

    remediation_hint = (
        'Before proceeding with the upgrade, review and remove packages from older '
        'RHEL releases:\n\n'
        '1. Review the list of affected packages\n'
        '2. Remove packages using: yum remove <package-name>\n'
        '3. For vendor/ISV software, contact the vendor for packages compatible with '
        'the target RHEL version\n'
        '4. For custom-built packages, rebuild them for the current RHEL version\n'
        '5. Contact Red Hat Support if you need assistance with package migration'
    )

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Remediation(hint=remediation_hint),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.RelatedResource('package', 'rpm'),
    ])
