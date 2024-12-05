from leapp.models import DistributionSignedRPM
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, run

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from repos.system_upgrade.el9toel10.models.mysql import MySQLConfiguration
else:
    from leapp.models import MySQLConfiguration

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

SERVICE_OVERRIDE_PATH = '/etc/systemd/system/mysqld.service.d/override.conf'


def _check_incompatible_config() -> set[str]:
    """
    Get incompatible configuration options. Since MySQL can have basically
    unlimited number of config files that can link to one another, most
    convenient way is running `mysqld` command with `--validate-config 
    --log-error-verbosity=2` arguments. Validate config only validates the
    config, without starting the MySQL server. Verbosity=2 is required to show
    deprecated options - which are removed after upgrade.

    Example output:
    2024-12-18T11:40:04.725073Z 0 [Warning] [MY-011069] [Server]
    The syntax '--old' is deprecated and will be removed in a future release.

    Returns:
        set[str]: Config options found that will be removed
    """

    found_options = set()
    stderr = run(['mysqld', '--validate-config', '--log-error-verbosity=2'],
                 checked=False)['stderr']

    if 'deprecated' in stderr:
        found_options = {arg for arg
                         in REMOVED_ARGS
                         if arg in stderr}
    return found_options


def _check_incompatible_launch_param() -> set[str]:
    """
    Get incompatible launch parameters from systemd service override file
    located at /etc/systemd/system/mysqld.service.d/override.conf

    Returns:
        set[str]: Launch parameters found that will be removed
    """

    found_arguments = set()
    try:
        with open(SERVICE_OVERRIDE_PATH) as f:
            file_content = f.read()
            found_arguments = {arg for arg
                               in REMOVED_ARGS
                               if arg in file_content}
    except OSError:
        # File probably doesn't exist, ignore it and pass
        pass

    return found_arguments


def check_status(_context=api) -> MySQLConfiguration:
    """
    Check whether MySQL is installed and if so whether config is compatible with
    newer version.

    Returns:
        MySQLConfiguration: Current status of MySQL on the system
    """

    mysql_present = has_package(DistributionSignedRPM, 'mysql-server', context=_context)

    found_options = []
    found_arguments = []
    if mysql_present:
        found_options = list(_check_incompatible_config())
        found_arguments = list(_check_incompatible_launch_param())

    return MySQLConfiguration(mysql_present=mysql_present,
                              removed_options=found_options,
                              removed_arguments=found_arguments)
