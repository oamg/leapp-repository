from leapp import reporting
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.common.rpms import has_package
from leapp.models import DistributionSignedRPM


def _report_server_installed():
    """
    Create report on mysql-server package installation detection.

    Should remind user about present MySQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.
    """
    reporting.create_report([
        reporting.Title('Further action to upgrade MySQL might be needed'),
        reporting.Summary(
            'The MySQL server component will be reinstalled during the upgrade with a {target_distro} 9'
            ' version. Since {target_distro} 9 includes the same MySQL version 8.0 by default, no action'
            ' should be required and there should not be any compatibility issues. However,'
            ' it is still advisable to follow the documentation on this topic for up to date'
            ' recommendations.'
            ' Keep in mind that MySQL 8.0, which is the default in {target_distro} 9, will reach the end'
            ' of \'Extended Support\' in April 2026. As such it is advisable to upgrade to'
            ' MySQL version 8.4, which is provided via a module. MySQL 8.4 is also the'
            ' default version for {target_distro} 10, therefore having MySQL 8.4 on the {target_distro} 9 system'
            ' will make a future upgrade process to {target_distro} 10 smoother.'.format_map(
                DISTRO_REPORT_NAMES
            )
        ),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating MySQL databases from RHEL 8 to RHEL 9',
                               url='https://access.redhat.com/articles/7099753'),
        reporting.RelatedResource('package', 'mysql-server'),
        reporting.Remediation(hint=(
            'Dump or backup your data before proceeding with the upgrade '
            'and consult attached article '
            '\'Migrating MySQL databases from RHEL 8 to RHEL 9\' '
            'with up to date recommended steps before and after the upgrade.'
        )),
    ])


def process():
    """
    Create reports according to detected MySQL packages.

    Create the report if the mysql-server rpm (RH signed) is installed.
    """
    has_server = has_package(DistributionSignedRPM, 'mysql-server')

    if has_server:
        _report_server_installed()
