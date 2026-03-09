import warnings

from leapp.libraries.stdlib import api
from leapp.models import RpmTransactionTasks

GSD_SERVER_DEFAULTS_PKG = 'gnome-settings-daemon-server-defaults'
GRAPHICAL_SERVER_ENV = 'graphical-server-environment'

no_dnf = False
try:
    import dnf
except ImportError:
    no_dnf = True
    warnings.warn('package `dnf` is unavailable', ImportWarning)


def _is_graphical_server_environment_installed():
    """
    Return True if the graphical-server-environment comps environment group
    is installed on the source system, False otherwise.
    """
    if no_dnf:
        api.current_logger().warning(
            'dnf Python module is not available; cannot check for installed comps environments.'
        )
        return False

    try:
        base = dnf.Base()
        swdb = base.history.swdb
        items = swdb.getCompsEnvironmentItemsByPattern(GRAPHICAL_SERVER_ENV)
        return len(items) > 0
    except Exception as e:  # pylint: disable=broad-except
        api.current_logger().warning(
            'Failed to query dnf history for installed comps environments: {}'.format(e)
        )
        return False


def process():
    if not _is_graphical_server_environment_installed():
        api.current_logger().debug(
            'The {} comps environment is not installed; skipping.'.format(GRAPHICAL_SERVER_ENV)
        )
        return

    api.current_logger().info(
        'The {} comps environment is installed; scheduling installation of {} for the upgrade.'.format(
            GRAPHICAL_SERVER_ENV, GSD_SERVER_DEFAULTS_PKG
        )
    )
    api.produce(RpmTransactionTasks(to_install=[GSD_SERVER_DEFAULTS_PKG]))
