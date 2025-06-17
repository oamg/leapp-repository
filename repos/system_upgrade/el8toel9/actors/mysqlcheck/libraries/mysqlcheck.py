from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM

# Summary for mysql-server report
# TODO: Fix versions
report_server_inst_summary = (
    'MySQL server component will be reinstalled during upgrade with RHEL 9 version. '
    'Since RHEL 9 includes the same version by default, no action should be '
    'needed and there shouldn\'t be any compatibility issues. It is still advisable '
    'to follow documentation/article on this topic for up to date recommendations. '
    'Keep in mind that MySQL version 8.0, which is present as a default in RHEL 9, '
    'will go out of the \'Extended Support\' in April 2026. MySQL 8.4 will be '
    'provided in RHEL 9 via module, and it is advisable to upgrade to that version. '
    'MySQL 8.4 is also the default version for RHEL 10, so having the MySQL 8.4 '
    'on RHEL 9 system will make the process of upgrading to RHEL 10 even smoother.'
)

report_server_inst_hint = (
    'Dump or backup your data before proceeding with the upgrade '
    'and consult attached article '
    '\'Migrating MySQL databases from RHEL 8 to RHEL 9\' '
    'with up to date recommended steps before and after the upgrade.'
)

# TODO: Replace with mysql-report
# Link URL for mysql-server report
report_server_inst_link_url = 'https://access.redhat.com/articles/7099753'


def _report_server_installed():
    """
    Create report on mysql-server package installation detection.

    Should remind user about present MySQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.
    """
    reporting.create_report([
        reporting.Title('Further action to upgrade MySQL might be needed'),
        reporting.Summary(report_server_inst_summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating MySQL databases from RHEL 8 to RHEL 9',
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
