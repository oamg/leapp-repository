from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM

# Summary for postgresql-server report
report_server_inst_summary = (
    'PostgreSQL server component will be upgraded. Since RHEL-9 includes'
    ' PostgreSQL server 13 by default, which is incompatible with 9.6, 10 and 12'
    ' included in RHEL-8, it is necessary to proceed with additional steps'
    ' for the complete upgrade of the PostgreSQL data.'
)

report_server_inst_hint = (
    'Back up your data before proceeding with the upgrade'
    ' and follow steps in the documentation section "Migrating to a RHEL 9 version of PostgreSQL"'
    ' after the upgrade.'
)

# Link URL for postgresql-server report
report_server_inst_link_url = 'https://access.redhat.com/articles/6654721'


def _report_server_installed():
    """
    Create report on postgresql-server package installation detection.

    Should remind user about present PostgreSQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.
    """
    reporting.create_report([
        reporting.Title('PostgreSQL (postgresql-server) has been detected on your system'),
        reporting.Summary(report_server_inst_summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating to a RHEL 9 version of PostgreSQL',
                               url=report_server_inst_link_url),
        reporting.RelatedResource('package', 'postgresql-server'),
        reporting.Remediation(hint=report_server_inst_hint),
        ])


def report_installed_packages(_context=api):
    """
    Create reports according to detected PostgreSQL packages.

    Create the report if the postgresql-server rpm (RH signed) is installed.
    """
    has_server = has_package(InstalledRedHatSignedRPM, 'postgresql-server', context=_context)

    if has_server:
        # postgresql-server
        _report_server_installed()
