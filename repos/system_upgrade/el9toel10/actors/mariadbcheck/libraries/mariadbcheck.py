from leapp import reporting
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM


def _report_server_installed():
    """
    Create report on mariadb-server package installation detection.

    Should remind user about present MariaDB server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.
    """
    summary = (
        'MariaDB server component will be upgraded.'
        ' Since {target_distro} 10 includes MariaDB server 10.11 by default,'
        ' which is incompatible with 10.5 included in {source_distro} 9 as default stream,'
        ' it is necessary to proceed with additional steps for the complete upgrade of the MariaDB data.'
    ).format_map(DISTRO_REPORT_NAMES)

    hint = (
        'Back up your data before proceeding with the upgrade and follow'
        ' steps in the documentation section "Migrating to a RHEL 10 version of'
        ' MariaDB" after the upgrade. If the database has already been'
        ' upgraded, meaning the system is already using MariaDB 10.11 then no'
        ' further actions are required.'
    )

    reporting.create_report([
        reporting.Title('MariaDB (mariadb-server) has been detected on your system'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating to a RHEL 10 version of MariaDB',
                               url='https://access.redhat.com/articles/7097551'),
        reporting.RelatedResource('package', 'mariadb-server'),
        reporting.Remediation(hint=hint),
    ])


def report_installed_packages(_context=api):
    """
    Create reports according to detected MariaDB packages.

    Create the report if the mariadb-server rpm (RH signed) is installed.
    """
    has_server = has_package(DistributionSignedRPM, 'mariadb-server', context=_context)

    if has_server:
        _report_server_installed()
