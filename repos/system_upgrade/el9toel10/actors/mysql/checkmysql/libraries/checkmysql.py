from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import MySQLConfiguration
from leapp.exceptions import StopActorExecutionError

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from repos.system_upgrade.el9toel10.models.mysql import MySQLConfiguration
else:
    from leapp.models import MySQLConfiguration

FMT_LIST_SEPARATOR = '\n    - '

# https://dev.mysql.com/doc/refman/8.0/en/server-system-variables.html
# https://dev.mysql.com/doc/refman/8.0/en/server-options.html
# https://dev.mysql.com/doc/refman/8.4/en/mysql-nutshell.html
REMOVED_ARGS = [
    '--avoid-temporal-upgrade',
    'avoid_temporal_upgrade',
    '--show-old-temporals',
    'show_old_temporals',
    '--old',
    '--new',
    '--default-authentication-plugin',
    'default_authentication_plugin',
    '--no-dd-upgrade',
    '--language',
    '--ssl',
    '--admin-ssl',
    '--character-set-client-handshake',
    '--old-style-user-limits',
]

# Link URL for mysql-server report
REPORT_SERVER_INST_LINK_URL = 'https://access.redhat.com/articles/7099234'


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
        reporting.Title('Further action to upgrade MySQL might be needed'),
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
            '\'Migrating MySQL databases from RHEL 9 to RHEL 10\' '
            'with up to date recommended steps before and after the upgrade.'
        )),
        ])


def _generate_deprecated_config_report(found_options: set | list,
                                       found_arguments: set | list) -> None:
    """
    Create report on mysql-server deprecated configuration.

    Apart from showing user the article for upgrade process, we inform the
    user that there are deprecated configuration options being used and
    proceeding with upgrade will result in MySQL server failing to start.
    """

    generated_list = ''
    if found_options:
        generated_list += (
            'Following configuration options won\'t work on a new version '
            'of MySQL after upgrading and have to be removed from configuration files:'
            )

        for arg in found_options:
            generated_list += FMT_LIST_SEPARATOR + arg

        generated_list += (
            '\nDefault configuration file is present at `/etc/my.cnf`\n'
        )

    if found_arguments:
        generated_list += (
            'Following startup arguments won\'t work on a new version '
            'of MySQL after upgrading and have to be removed from '
            'systemd service files:'
            )

        for arg in found_arguments:
            generated_list += FMT_LIST_SEPARATOR + arg

        generated_list += (
            '\nDefault service override file is present at '
            '`/etc/systemd/system/mysqld.service.d/override.conf`\n'
        )

    reporting.create_report([
        reporting.Title('MySQL is using configuration that will be invalid after upgrade'),
        reporting.Summary((
            'MySQL server component will be upgraded. '
            'Since RHEL-10 includes MySQL server 8.4 by default, '
            'it is necessary to proceed with additional steps. '
            'Some options that are currently used in MySQL configuration are '
            'deprecated and will result in MySQL server failing to start '
            'after upgrading. '
            'After RHEL upgrade is completed MySQL server should automatically upgrade all '
            'data on first start in simple setups. In more '
            'complicated setups manual intervention might be needed.'
        )),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating MySQL databases from RHEL 9 to RHEL 10',
                               url=REPORT_SERVER_INST_LINK_URL),
        reporting.RelatedResource('package', 'mysql-server'),
        reporting.Remediation(hint=(
            'To ensure smooth upgrade process it is strongly recommended to '
            'remove deprecated config options \n' +
            generated_list +
            'Dump or backup your data before proceeding with the upgrade '
            'and consult attached article '
            '\'Migrating MySQL databases from RHEL 9 to RHEL 10\' '
            'with up to date recommended steps before and after the upgrade.'
        )),
        ])


def _generate_report(found_options: set | list, found_arguments: set | list) -> None:
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
