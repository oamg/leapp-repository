import os

from leapp import reporting
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.common.rhsm import skip_rhsm

# If LEAPP_NO_RHSM is set, subscription-manager and product-id will not be
# considered as required when checking whether the required plugins are enabled.
REQUIRED_YUM_PLUGINS = {'subscription-manager', 'product-id'}
FMT_LIST_SEPARATOR = '\n    - '


def check_required_yum_plugins_enabled(pkg_manager_info):
    """
    Checks whether the yum plugins required by the IPU are enabled.

    If they are not enabled, a report is produced informing the user about it.

    :param pkg_manager_info: PkgManagerInfo
    """

    missing_required_plugins = REQUIRED_YUM_PLUGINS - set(pkg_manager_info.enabled_plugins)

    if skip_rhsm():
        missing_required_plugins -= {'subscription-manager', 'product-id'}

    if missing_required_plugins:
        missing_required_plugins_text = ''
        for missing_plugin in missing_required_plugins:
            missing_required_plugins_text += '{0}{1}'.format(FMT_LIST_SEPARATOR, missing_plugin)

        if get_source_major_version() == '7':
            pkg_manager = 'YUM'
            pkg_manager_config_path = '/etc/yum.conf'
            plugin_configs_dir = '/etc/yum/pluginconf.d'
        else:
            # On RHEL8+ the yum package might not be installed
            pkg_manager = 'DNF'
            pkg_manager_config_path = '/etc/dnf/dnf.conf'
            plugin_configs_dir = '/etc/dnf/plugins'

        # pkg_manager_config_path - enable/disable plugins globally
        # subscription_manager_plugin_conf, product_id_plugin_conf - plugins can be disabled individually
        subscription_manager_plugin_conf = os.path.join(plugin_configs_dir, 'subscription-manager.conf')
        product_id_plugin_conf = os.path.join(plugin_configs_dir, 'product-id.conf')

        remediation_commands = [
            'sed -i \'s/^plugins=0/plugins=1/\' \'{0}\''.format(pkg_manager_config_path),
            'sed -i \'s/^enabled=0/enabled=1/\' \'{0}\''.format(subscription_manager_plugin_conf),
            'sed -i \'s/^enabled=0/enabled=1/\' \'{0}\''.format(product_id_plugin_conf)
        ]

        reporting.create_report([
            reporting.Title('Required {0} plugins are not being loaded.'.format(pkg_manager)),
            reporting.Summary(
                'The following {0} plugins are not being loaded: {1}'.format(pkg_manager,
                                                                             missing_required_plugins_text)
            ),
            reporting.Remediation(
                hint='If you have yum plugins globally disabled, please enable them by editing the {0}. '
                     'Individually, the {1} plugins can be enabled in their corresponding configurations found at: {2}'
                     .format(pkg_manager_config_path, pkg_manager, plugin_configs_dir),
                # Provide all commands as one due to problems with satellites
                commands=[['bash', '-c', '"{0}"'.format('; '.join(remediation_commands))]]
            ),
            reporting.RelatedResource('file', pkg_manager_config_path),
            reporting.RelatedResource('file', subscription_manager_plugin_conf),
            reporting.RelatedResource('file', product_id_plugin_conf),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
        ])
