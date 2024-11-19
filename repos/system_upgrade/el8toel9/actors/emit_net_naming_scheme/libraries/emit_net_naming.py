from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_env, version
from leapp.libraries.stdlib import api
from leapp.models import (
    KernelCmdline,
    KernelCmdlineArg,
    RpmTransactionTasks,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeKernelCmdlineArgTasks
)

NET_NAMING_SYSATTRS_RPM_NAME = 'rhel-net-naming-sysattrs'


def is_net_scheme_compatible_with_current_cmdline():
    kernel_cmdline = next(api.consume(KernelCmdline), None)
    if not kernel_cmdline:
        # Super unlikely
        raise StopActorExecutionError('Did not receive any KernelCmdline messages.')

    allows_predictable_names = True
    already_has_a_net_naming_scheme = False
    for param in kernel_cmdline.parameters:
        if param.key == 'net.ifnames':
            if param.value == '0':
                allows_predictable_names = False
            elif param.value == '1':
                allows_predictable_names = True
        if param.key == 'net.naming-scheme':
            # We assume that the kernel cmdline does not contain invalid entries, namely,
            # that the net.naming-scheme refers to a valid scheme.
            already_has_a_net_naming_scheme = True

    is_compatible = allows_predictable_names and not already_has_a_net_naming_scheme

    msg = ('Should net.naming-scheme be added to kernel cmdline: %s. '
           'Reason: allows_predictable_names=%s, already_has_a_net_naming_scheme=%s')
    api.current_logger().info(msg, 'yes' if is_compatible else 'no',
                              allows_predictable_names,
                              already_has_a_net_naming_scheme)

    return is_compatible


def emit_msgs_to_use_net_naming_schemes():
    is_feature_enabled = get_env('LEAPP_DISABLE_NET_NAMING_SCHEMES', '0') != '1'
    is_upgrade_8to9 = version.get_target_major_version() == '9'
    is_net_naming_enabled_and_permitted = is_feature_enabled and is_upgrade_8to9
    if not is_net_naming_enabled_and_permitted:
        return

    # The package should be installed regardless of whether we will modify the cmdline -
    # if the cmdline already contains net.naming-scheme, then the package will be useful
    # in both, the upgrade environment and on the target system.
    pkgs_to_install = [NET_NAMING_SYSATTRS_RPM_NAME]
    api.produce(TargetUserSpaceUpgradeTasks(install_rpms=pkgs_to_install))
    api.produce(RpmTransactionTasks(to_install=pkgs_to_install))

    if not is_net_scheme_compatible_with_current_cmdline():
        return

    naming_scheme = 'rhel-{0}.0'.format(version.get_source_major_version())
    cmdline_args = [KernelCmdlineArg(key='net.naming-scheme', value=naming_scheme)]
    api.produce(UpgradeKernelCmdlineArgTasks(to_add=cmdline_args))
    api.produce(TargetKernelCmdlineArgTasks(to_add=cmdline_args))
