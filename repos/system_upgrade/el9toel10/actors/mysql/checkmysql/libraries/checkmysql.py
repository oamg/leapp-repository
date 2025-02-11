from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from repos.system_upgrade.el9toel10.models.mysql import MySQLConfiguration
else:
    from leapp.models import MySQLConfiguration

FMT_LIST_SEPARATOR = '\n    - '

# Link URL for mysql-server report
REPORT_SERVER_INST_LINK_URL = 'https://access.redhat.com/articles/7099234'


def _formatted_list_output(input_list, sep=FMT_LIST_SEPARATOR):
    return ['{}{}'.format(sep, item) for item in input_list]


def _generate_mysql_present_report() -> None:
    """
    Create report on mysql-server package installation detection.

    Should remind user about present MySQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.

    This report is used in case MySQL package is detected, but no
    immediate action is needed.
    """
    reporting.create_report([
        reporting.Title('Manual migration of data from MySQL database might be needed'),
        reporting.Summary((
            'MySQL server component will be upgraded. '
            'Since RHEL-10 includes MySQL server 8.4 by default, '
            'it might be necessary to proceed with additional steps after '
            'RHEL upgrade is completed. In simple setups MySQL server should '
            'automatically upgrade all data on first start, but in more '
            'complicated setups manual intervention might be needed.'
        )),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating MySQL databases from RHEL 9 to RHEL 10',
                               url=REPORT_SERVER_INST_LINK_URL),
        reporting.RelatedResource('package', 'mysql-server'),
        reporting.Remediation(hint=(
            'Dump or backup your data before proceeding with the upgrade '
            'and consult attached article '
            '"Migrating MySQL databases from RHEL 9 to RHEL 10" '
            'with up to date recommended steps before and after the upgrade.'
        )),
        ])


def _generate_deprecated_config_report(found_options: list,
                                       found_arguments: list) -> None:
    """
    Create report on mysql-server deprecated configuration.

    Apart from showing user the article for upgrade process, we inform the
    user that there are deprecated configuration options being used and
    proceeding with upgrade will result in MySQL server failing to start.
    """

    summary_list = []
    remedy_list = []
    if found_options:
        summary_list.append(
            'Following incompatible configuration options have been detected:{}'
            '\nDefault configuration file is present at `/etc/my.cnf`'
            .format(''.join(_formatted_list_output(found_options)))
        )
        remedy_list.append('Drop all deprecated configuration options before the upgrade.')

    if found_arguments:
        summary_list.append(
            'Following detected startup arguments in systemd service files'
            'will not work with the new MySQL after upgrading:{}\n'
            'Default service override file is present at '
            '`/etc/systemd/system/mysqld.service.d/override.conf`'
            .format(''.join(_formatted_list_output(found_arguments)))
        )
        remedy_list.append(
            'Drop all detected problematic startup arguments from '
            'the customized systemd service file.'
        )

    reporting.create_report([
        reporting.Title('Detected incompatible MySQL configuration'),
        reporting.Summary((
            'Current MySQL configuration is not compatible with the new MySQL '
            'version on the target system and '
            'will result in MySQL server failing to start after upgrading.'
            '\n\n{}'
            .format('\n\n'.join(summary_list))
        )),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating MySQL databases from RHEL 9 to RHEL 10',
                               url=REPORT_SERVER_INST_LINK_URL),
        reporting.RelatedResource('package', 'mysql-server'),
        reporting.RelatedResource('file', '/etc/my.cnf'),
        reporting.RelatedResource('file', '/etc/systemd/system/mysqld.service.d/override.conf'),
        reporting.Remediation(hint=(
            'To ensure smooth upgrade process it is strongly recommended to:{}'
            .format(''.join(''._formatted_list_output(remedy_list)))
        )),
        ])


def _generate_report(found_options: list, found_arguments: list) -> None:
    """
    Create report on mysql-server package installation detection.

    Should remind user about present MySQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.
    """

    if found_arguments or found_options:
        _generate_deprecated_config_report(found_options, found_arguments)
    else:
        _generate_mysql_present_report()


def process() -> None:
    msg: MySQLConfiguration = next(api.consume(MySQLConfiguration), None)
    if not msg:
        raise StopActorExecutionError('Expected MySQLConfiguration, but got None')

    if msg.mysql_present:
        _generate_report(msg.removed_options, msg.removed_arguments)
    else:
        api.current_logger().debug(
            'mysql-server package not found, no report generated'
        )
