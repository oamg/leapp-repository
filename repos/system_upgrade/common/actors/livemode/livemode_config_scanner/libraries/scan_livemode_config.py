from leapp.configs.actor import livemode as livemode_config_lib
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture, get_env
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, LiveModeConfig

LIVEMODE_CONFIG_LOCATION = '/etc/leapp/files/devel-livemode.ini'
DEFAULT_SQUASHFS_PATH = '/var/lib/leapp/live-upgrade.img'


def should_scan_config():
    is_unsupported = get_env('LEAPP_UNSUPPORTED', '0') == '1'
    is_livemode_enabled = get_env('LEAPP_DEVEL_ENABLE_LIVE_MODE', '0') == '1'

    if not is_unsupported:
        api.current_logger().debug('Will not scan livemode config - the upgrade is not unsupported.')
        return False

    if not is_livemode_enabled:
        api.current_logger().debug('Will not scan livemode config - the live mode is not enabled.')
        return False

    if not architecture.matches_architecture(architecture.ARCH_X86_64):
        api.current_logger().debug('Will not scan livemode config - livemode is currently limited to x86_64.')
        details = 'Live upgrades are currently limited to x86_64 only.'
        raise StopActorExecutionError(
            'CPU architecture does not meet requirements for live upgrades',
            details={'Problem': details}
        )

    if not has_package(InstalledRPM, 'squashfs-tools'):
        # This feature is not to be used by standard users, so stopping the upgrade and providing
        # the developer a speedy feedback is OK.
        raise StopActorExecutionError(
            'The \'squashfs-tools\' is not installed',
            details={'Problem': 'The \'squashfs-tools\' is required for the live mode.'}
        )

    return True


def scan_config_and_emit_message():
    if not should_scan_config():
        return

    api.current_logger().info('Loading livemode config from %s', LIVEMODE_CONFIG_LOCATION)

    config = api.current_actor().config[livemode_config_lib.LIVEMODE_CONFIG_SECTION]

    # Mapping from model field names to configuration fields - because we might have
    # changed some configuration field names for configuration to be more
    # comprehensible for our users.
    model_fields_to_config_options_map = {
        'url_to_load_squashfs_from': livemode_config_lib.URLToLoadSquashfsImageFrom,
        'squashfs_fullpath': livemode_config_lib.SquashfsImagePath,
        'dracut_network': livemode_config_lib.DracutNetwork,
        'setup_network_manager': livemode_config_lib.SetupNetworkManager,
        'additional_packages': livemode_config_lib.AdditionalPackages,
        'autostart_upgrade_after_reboot': livemode_config_lib.AutostartUpgradeAfterReboot,
        'setup_opensshd_with_auth_keys': livemode_config_lib.SetupOpenSSHDUsingAuthKeys,
        'setup_passwordless_root': livemode_config_lib.SetupPasswordlessRoot,
        'capture_upgrade_strace_into': livemode_config_lib.CaptureSTraceInfoInto
    }

    # Read values of model fields from user-supplied configuration according to the above mapping
    config_msg_init_kwargs = {}
    for model_field_name, config_field in model_fields_to_config_options_map.items():
        config_msg_init_kwargs[model_field_name] = config[config_field.name]

    # Some fields of the LiveModeConfig are historical and can no longer be changed by the user
    # in the config. Therefore, we just hard-code them here.
    config_msg_init_kwargs['is_enabled'] = True

    config_msg = LiveModeConfig(**config_msg_init_kwargs)
    api.produce(config_msg)
