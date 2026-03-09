from leapp.libraries.stdlib import api
from leapp.models import InstalledDNFComps, RpmTransactionTasks

GSD_SERVER_DEFAULTS_PKG = 'gnome-settings-daemon-server-defaults'
GRAPHICAL_SERVER_ENV = 'graphical-server-environment'


def _is_graphical_server_environment_installed(installed_comps):
    """
    Return True if the `GRAPHICAL_SERVER_ENV` comps environment group
    is installed on the source system, False otherwise.
    """
    return any(env.id == GRAPHICAL_SERVER_ENV for env in installed_comps.environments)


def process():
    installed_comps = next(api.consume(InstalledDNFComps), None)
    if not installed_comps:
        api.current_logger().warning(
            'Missing information about installed DNF comps: No InstalledDNFComps message.'
        )
        return

    if not _is_graphical_server_environment_installed(installed_comps):
        api.current_logger().debug(
            'The {} comps environment is not installed; skipping.'
            .format(GRAPHICAL_SERVER_ENV)
        )
        return

    api.current_logger().info(
        'The {} comps environment is installed.'
        ' Scheduling installation of {} for the upgrade.'
        .format(GRAPHICAL_SERVER_ENV, GSD_SERVER_DEFAULTS_PKG)
    )
    api.produce(RpmTransactionTasks(to_install=[GSD_SERVER_DEFAULTS_PKG]))
