try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture, get_env
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, LiveModeConfig
from leapp.models.fields import ModelViolationError

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
    parser = configparser.ConfigParser()

    try:
        parser.read((LIVEMODE_CONFIG_LOCATION, ))
    except configparser.ParsingError as error:
        api.current_logger().error('Failed to parse live mode configuration due to the following error: %s', error)

        details = 'Failed to read livemode configuration due to the following error: {0}.'
        raise StopActorExecutionError(
            'Failed to read livemode configuration',
            details={'Problem': details.format(error)}
        )

    livemode_section = 'livemode'
    if not parser.has_section(livemode_section):
        details = 'The configuration is missing the \'[{0}]\' section'.format(livemode_section)
        raise StopActorExecutionError(
            'Live mode configuration does not have the required structure',
            details={'Problem': details}
        )

    config_kwargs = {
        'is_enabled': True,
        'url_to_load_squashfs_from': None,
        'squashfs_fullpath': DEFAULT_SQUASHFS_PATH,
        'dracut_network': None,
        'setup_network_manager': False,
        'additional_packages': [],
        'autostart_upgrade_after_reboot': True,
        'setup_opensshd_with_auth_keys': None,
        'setup_passwordless_root': False,
        'capture_upgrade_strace_into': None
    }

    config_str_options = (
        'url_to_load_squashfs_from',
        'squashfs_fullpath',
        'dracut_network',
        'setup_opensshd_with_auth_keys',
        'capture_upgrade_strace_into'
    )

    config_list_options = (
        'additional_packages',
    )

    config_bool_options = (
        'setup_network_manager',
        'setup_passwordless_root',
        'autostart_upgrade_after_reboot',
    )

    for config_option in config_str_options:
        if parser.has_option(livemode_section, config_option):
            config_kwargs[config_option] = parser.get(livemode_section, config_option)

    for config_option in config_bool_options:
        if parser.has_option(livemode_section, config_option):
            config_kwargs[config_option] = parser.getboolean(livemode_section, config_option)

    for config_option in config_list_options:
        if parser.has_option(livemode_section, config_option):
            option_val = parser.get(livemode_section, config_option)
            option_list = (opt_val.strip() for opt_val in option_val.split(','))
            option_list = [opt for opt in option_list if opt]
            config_kwargs[config_option] = option_list

    try:
        config = LiveModeConfig(**config_kwargs)
    except ModelViolationError as error:
        raise StopActorExecutionError('Failed to parse livemode configuration.', details={'Problem': str(error)})

    api.produce(config)
