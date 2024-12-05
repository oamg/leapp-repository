from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM

# Summary for mysql-server report
report_server_inst_summary = (
    'MySQL server component will be upgraded. Since RHEL-10 includes'
    ' MySQL server 8.4 by default, which is incompatible with 8.0'
    ' included in RHEL-9, it is necessary to proceed with additional steps'
    ' for the complete upgrade of the MySQL data.'
)

report_server_inst_hint = (
    'Back up your data before proceeding with the upgrade'
    ' and follow steps in the documentation section "Migrating to a RHEL 10 version of MySQL"'
    ' after the upgrade.'
)

# Link URL for mysql-server report
report_server_inst_link_url = 'https://access.redhat.com/articles/7099234'


def _report_server_installed():
    """
    Create report on mysql-server package installation detection.

    Should remind user about present MySQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.
    """
    reporting.create_report([
        reporting.Title('MySQL (mysql-server) has been detected on your system'),
        reporting.Summary(report_server_inst_summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating to a RHEL 10 version of MySQL',
                               url=report_server_inst_link_url),
        reporting.RelatedResource('package', 'mysql-server'),
        reporting.Remediation(hint=report_server_inst_hint),
        ])


def report_installed_packages(_context=api):
    """
    Create reports according to detected MySQL packages.

    Create the report if the mysql-server rpm (RH signed) is installed.
    """
    has_server = has_package(DistributionSignedRPM, 'mysql-server', context=_context)

    if has_server:
        _report_server_installed()
