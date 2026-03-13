from leapp import reporting
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM


def _report_server_installed():
    """
    Create report on postgresql-server package installation detection.

    Should remind user about present PostgreSQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.
    """
    summary = (
        'PostgreSQL server component will be upgraded. Since {target_distro} 9'
        ' includes PostgreSQL server 13 by default, which is incompatible with 9.6,'
        ' 10 and 12 included in {source_distro} 8, in those cases, it is necessary'
        ' to proceed with additional steps for the complete upgrade of the PostgreSQL'
        ' data. If the database has already been upgraded, meaning the system is'
        ' already using PostgreSQL 13, then no further actions are required.'
    ).format_map(DISTRO_REPORT_NAMES)

    hint = (
        'Back up your data before proceeding with the upgrade'
        ' and follow steps in the documentation section "Migrating to a RHEL 9 version of PostgreSQL"'
        ' after the upgrade.'
    )

    reporting.create_report(
        [
            reporting.Title(
                "PostgreSQL (postgresql-server) has been detected on your system"
            ),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([reporting.Groups.SERVICES]),
            reporting.ExternalLink(
                title="Migrating to a RHEL 9 version of PostgreSQL",
                url='https://access.redhat.com/articles/6654721',
            ),
            reporting.RelatedResource("package", "postgresql-server"),
            reporting.Remediation(hint=hint),
        ]
    )


def report_installed_packages(_context=api):
    """
    Create reports according to detected PostgreSQL packages.

    Create the report if the postgresql-server rpm (RH signed) is installed.
    """
    has_server = has_package(DistributionSignedRPM, 'postgresql-server', context=_context)

    if has_server:
        # postgresql-server
        _report_server_installed()
