from leapp.models import fields, Model
from leapp.topics import BootPrepTopic, SystemInfoTopic, TransactionTopic


class LiveModeConfig(Model):
    topic = SystemInfoTopic

    is_enabled = fields.Boolean()
    """ True if the live mode is enabled """

    setup_passwordless_root = fields.Boolean(default=False)
    """ Setup passwordless root for the live image used during the upgrade. """

    url_to_load_squashfs_from = fields.Nullable(fields.String())
    """
    Url pointing to the squashfs image.

    if not set, the upgrade will boot locally
    example: "http://192.168.122.1/live-upgrade.img"
    """

    squashfs_fullpath = fields.String()
    """ Path to where the squashfs image should be stored. """

    dracut_network = fields.Nullable(fields.String())
    """
    Dracut network arguments.

    Required if the url_to_lead_squashfs_from is set

    example1: "ip=dhcp"
    example2: "ip=192.168.122.146::192.168.122.1:255.255.255.0:foo::none"
    """

    setup_network_manager = fields.Boolean(default=False)
    """ Enable the NetworkManager """

    additional_packages = fields.List(fields.String(), default=[])
    """ List of extra packages to include in the target userspace """

    autostart_upgrade_after_reboot = fields.Boolean(default=True)
    """ Autostart the upgrade upon reboot """

    setup_opensshd_with_auth_keys = fields.Nullable(fields.String())
    """
    Setup SSHD using the authorized keys file.

    If empty, SSHD will not be enabled.

    example: "/root/.ssh/authorized_keys"
    """

    capture_upgrade_strace_into = fields.Nullable(fields.String())
    """
    File into which leapp upgrade service's strace output will be written.

    If empty, leapp will not be run under strace.

    example: "/var/lib/leapp/upgrade.strace"
    """


class LiveModeRequirementsTasks(Model):
    topic = TransactionTopic

    packages = fields.List(fields.String())
    """
    packages to be installed in the target userspace
    """


class LiveImagePreparationInfo(Model):
    """
    Information about how the upgrade live image is set up.
    """
    topic = BootPrepTopic

    has_passwordless_root = fields.Boolean(default=False)
    has_sshd = fields.Boolean(default=False)
    has_network_set_up = fields.Boolean(default=False)


class PrepareLiveImagePostTasks(Model):
    topic = BootPrepTopic


class LiveBootEntryTasks(Model):
    topic = BootPrepTopic
    grubby = fields.Boolean()


class LiveModeArtifacts(Model):
    topic = BootPrepTopic

    """
    Artifacts created for the Live Mode
    """
    squashfs_path = fields.String()
