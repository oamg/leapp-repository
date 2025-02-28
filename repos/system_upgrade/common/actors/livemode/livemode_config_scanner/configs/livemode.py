"""
Configuration keys for the 'livemode' feature.
"""

from leapp.actors.config import Config
from leapp.models import fields

LIVEMODE_CONFIG_SECTION = 'livemode'


class SquashfsImagePath(Config):
    section = LIVEMODE_CONFIG_SECTION
    name = "squashfs_image_path"
    type_ = fields.String()
    default = '/var/lib/leapp/live-upgrade.img'
    description = """
        Location where the squashfs image of the minimal target system will be placed.
    """


class AdditionalPackages(Config):
    section = LIVEMODE_CONFIG_SECTION
    name = "additional_packages"
    type_ = fields.List(fields.String())
    default = []
    description = """
        Additional packages to be installed into the squashfs image.

        Can be used to install various debugging utilities when connecting to the upgrade environment.
    """


class AutostartUpgradeAfterReboot(Config):
    section = LIVEMODE_CONFIG_SECTION
    name = "autostart_upgrade_after_reboot"
    type_ = fields.Boolean()
    default = True
    description = """
        If set to True, the upgrade will start automatically after the reboot. Otherwise a manual trigger is required.
    """


class SetupNetworkManager(Config):
    section = LIVEMODE_CONFIG_SECTION
    name = "setup_network_manager"
    type_ = fields.Boolean()
    default = False
    description = """
        Try enabling Network Manager in the squashfs image.

        If set to True, leapp will copy source system's Network Manager profiles into the squashfs image and
        enable the Network Manager service.
    """


class DracutNetwork(Config):
    section = LIVEMODE_CONFIG_SECTION
    name = "dracut_network"
    type_ = fields.String()
    default = ''
    description = """
        Dracut network arguments, required if the `url_to_load_squashfs_from` option is set.

        Example:
            ip=192.168.122.146::192.168.122.1:255.255.255.0:foo::none
    """


class URLToLoadSquashfsImageFrom(Config):
    section = LIVEMODE_CONFIG_SECTION
    name = "url_to_load_squashfs_image_from"
    type_ = fields.String()
    default = ''
    description = """
        Url pointing to the squashfs image that should be used for the upgrade environment.

        Example:
            http://192.168.122.1/live-upgrade.img
    """


class SetupPasswordlessRoot(Config):
    section = LIVEMODE_CONFIG_SECTION
    name = "setup_passwordless_root"
    type_ = fields.Boolean()
    default = False
    description = """
        If set to True, the root account of the squashfs image will have empty password. Use with caution.
    """


class SetupOpenSSHDUsingAuthKeys(Config):
    section = LIVEMODE_CONFIG_SECTION
    name = "setup_opensshd_using_auth_keys"
    type_ = fields.String()
    default = ''
    description = """
        If set to a non-empty string, openssh daemon will be setup within the squashfs image using the provided
        authorized keys.

        Example:
            /root/.ssh/authorized_keys
    """


class CaptureSTraceInfoInto(Config):
    section = LIVEMODE_CONFIG_SECTION
    name = "capture_strace_info_into"
    type_ = fields.String()
    default = ''
    description = """
        If set to a non-empty string, leapp will be executed under strace and results will be stored within
        the provided file path.
    """


livemode_cfg_fields = (
    AdditionalPackages,
    AutostartUpgradeAfterReboot,
    CaptureSTraceInfoInto,
    DracutNetwork,
    SetupNetworkManager,
    SetupOpenSSHDUsingAuthKeys,
    SetupPasswordlessRoot,
    SquashfsImagePath,
    URLToLoadSquashfsImageFrom,
)
