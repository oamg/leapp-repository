import os

from leapp import reporting
from leapp.libraries.common.rhsm import skip_rhsm

# If LEAPP_NO_RHSM is set, subscription-manager and product-id will not be
# considered as required when checking whether the required plugins are enabled.
REQUIRED_DNF_PLUGINS = {'subscription-manager', 'product-id'}
FMT_LIST_SEPARATOR = '\n    - '


def check_required_dnf_plugins_enabled(pkg_manager_info):
    """
    Checks whether the DNF plugins required by the IPU are enabled.

    If they are not enabled, a report is produced informing the user about it.

    :param pkg_manager_info: PkgManagerInfo
    """

    missing_required_plugins = REQUIRED_DNF_PLUGINS - set(pkg_manager_info.enabled_plugins)

    if skip_rhsm():
        missing_required_plugins -= {'subscription-manager', 'product-id'}

    if missing_required_plugins:
        missing_required_plugins_text = ''
        for missing_plugin in missing_required_plugins:
            missing_required_plugins_text += '{0}{1}'.format(FMT_LIST_SEPARATOR, missing_plugin)

        dnf_conf_path = '/etc/dnf/dnf.conf'
        plugin_configs_dir = '/etc/dnf/plugins'

        # dnf_conf_path - enable/disable plugins globally
        # rhsm_plugin_conf, product_id_plugin_conf - plugins can be disabled individually
        rhsm_plugin_conf = os.path.join(plugin_configs_dir, 'subscription-manager.conf')
        product_id_plugin_conf = os.path.join(plugin_configs_dir, 'product-id.conf')

        remediation_commands = [
            f'sed -i \'s/^plugins=0/plugins=1/\' \'{dnf_conf_path}\''
            f'sed -i \'s/^enabled=0/enabled=1/\' \'{rhsm_plugin_conf}\''
            f'sed -i \'s/^enabled=0/enabled=1/\' \'{product_id_plugin_conf}\''
        ]

        reporting.create_report([
            reporting.Title('Required DNF plugins are not being loaded.'),
            reporting.Summary(
                'The following DNF plugins are not being loaded: {}'.format(missing_required_plugins_text)
            ),
            reporting.Remediation(
                hint=(
                    'If you have DNF plugins globally disabled, please enable them by editing the {0}. '
                    'Individually, the DNF plugins can be enabled in their corresponding configurations found at: {1}'
                    .format(dnf_conf_path, plugin_configs_dir)
                ),
                # Provide all commands as one due to problems with satellites
                commands=[['bash', '-c', '"{0}"'.format('; '.join(remediation_commands))]]
            ),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/7028063',
                title='Why is Leapp preupgrade generating "Inhibitor: Required YUM plugins are not being loaded."'
            ),
            reporting.RelatedResource('file', dnf_conf_path),
            reporting.RelatedResource('file', rhsm_plugin_conf),
            reporting.RelatedResource('file', product_id_plugin_conf),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            # TODO add key
        ])
