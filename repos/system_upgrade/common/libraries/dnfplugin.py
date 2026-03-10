"""
DEPRECATED: This module has been moved to leapp.libraries.common.dnflibs.dnfplugin

This shim will be removed in a future version. Please update imports to:
    from leapp.libraries.common.dnflibs import dnfplugin
    # or
    from leapp.libraries.common import dnflibs
"""

from leapp.libraries.common.dnflibs import dnfplugin as _dnfplugin
from leapp.utils.deprecation import deprecated

# Re-export constants
DNF_PLUGIN_NAME = _dnfplugin.DNF_PLUGIN_NAME
DNF_PLUGIN_DATA_NAME = _dnfplugin.DNF_PLUGIN_DATA_NAME
DNF_PLUGIN_DATA_PATH = _dnfplugin.DNF_PLUGIN_DATA_PATH
DNF_PLUGIN_DATA_LOG_PATH = _dnfplugin.DNF_PLUGIN_DATA_LOG_PATH
DNF_DEBUG_DATA_PATH = _dnfplugin.DNF_DEBUG_DATA_PATH


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def install(target_basedir):
    """
    Installs our plugin to the DNF plugins.
    """
    return _dnfplugin.install(target_basedir)


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def build_plugin_data(target_repoids, debug, test, tasks, on_aws):
    """
    Generates a dictionary with the DNF plugin data.
    """
    return _dnfplugin.build_plugin_data(target_repoids, debug, test, tasks, on_aws)


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def create_config(context, target_repoids, debug, test, tasks, on_aws=False):
    """
    Creates the configuration data file for our DNF plugin.
    """
    return _dnfplugin.create_config(context, target_repoids, debug, test, tasks, on_aws)


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def backup_config(context):
    """
    Backs up the configuration data used for the plugin.
    """
    return _dnfplugin.backup_config(context)


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def backup_debug_data(context):
    """
    Performs the backup of DNF debug data
    """
    return _dnfplugin.backup_debug_data(context)


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def apply_workarounds(context=None):
    """
    Apply registered workarounds in the given context environment
    """
    return _dnfplugin.apply_workarounds(context)


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def install_initramdisk_requirements(packages, target_userspace_info, used_repos):
    """
    Performs the installation of packages into the initram disk
    """
    return _dnfplugin.install_initramdisk_requirements(packages, target_userspace_info, used_repos)


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def perform_transaction_install(target_userspace_info, storage_info, used_repos, tasks, plugin_info, xfs_info):
    """
    Performs the actual installation with the DNF rhel-upgrade plugin using the target userspace
    """
    return _dnfplugin.perform_transaction_install(
        target_userspace_info, storage_info, used_repos, tasks, plugin_info, xfs_info
    )


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def perform_transaction_check(target_userspace_info,
                              used_repos,
                              tasks,
                              xfs_info,
                              storage_info,
                              plugin_info,
                              target_iso=None):
    """
    Perform DNF transaction check using our plugin
    """
    return _dnfplugin.perform_transaction_check(
        target_userspace_info, used_repos, tasks, xfs_info, storage_info, plugin_info, target_iso
    )


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def perform_rpm_download(target_userspace_info,
                         used_repos,
                         tasks,
                         xfs_info,
                         storage_info,
                         plugin_info,
                         target_iso=None,
                         on_aws=False):
    """
    Perform RPM download including the transaction test using dnf with our plugin
    """
    return _dnfplugin.perform_rpm_download(
        target_userspace_info, used_repos, tasks, xfs_info, storage_info, plugin_info, target_iso, on_aws
    )


@deprecated(since='2026-03-10', message=(
    'This function has been moved to leapp.libraries.common.dnflibs.dnfplugin module. '
    'Please update your imports to use the new location.'
))
def perform_dry_run(target_userspace_info,
                    used_repos,
                    tasks,
                    xfs_info,
                    storage_info,
                    plugin_info,
                    target_iso=None,
                    on_aws=False):
    """
    Perform the dnf transaction test / dry-run using only cached data.
    """
    return _dnfplugin.perform_dry_run(
        target_userspace_info, used_repos, tasks, xfs_info, storage_info, plugin_info, target_iso, on_aws
    )
