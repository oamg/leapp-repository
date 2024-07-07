from leapp.models import fields, Model
from leapp.topics import BootPrepTopic, SystemInfoTopic, TransactionTopic


class LiveModeConfigFacts(Model):
    topic = SystemInfoTopic

    """
    the LiveOS artifact is built if enabled = 1
    default is 0
    """
    enabled = fields.Integer()

    setup_passwordless_root = fields.Boolean(default=False)
    """ Setup passwordless root for the live image used during the upgrade. """

    """
    url pointing to the squashfs image.
    default is "" (booting locally)
    example: "http://192.168.122.1/live-upgrade.img"
    """
    url = fields.Nullable(fields.String())

    """
    squashfs image storage filename (full path)
    """
    squashfs = fields.Nullable(fields.String())

    """
    include dnf cache into the image, default is 0
    """
    with_cache = fields.Integer()

    """
    temporary LiveOS directory
    """
    temp_dir = fields.Nullable(fields.String())

    """
    dracut network arguments, mandatory if url is not ""
    example1: "ip=dhcp"
    example2: "ip=192.168.122.146::192.168.122.1:255.255.255.0:foo::none"
    """
    dracut_network = fields.Nullable(fields.String())

    """
    enable the NetworkManager, default is 0
    """
    nm = fields.Integer()

    """
    list of extra packages to include in the target userspace
    example: ["tcpdump", "trace-cmd"]
    """
    packages = fields.List(fields.String())

    """
    autostart the upgrade upon reboot (or use upgrade.autostart=0 to disable)
    default is 1
    """
    autostart = fields.Integer()

    """
    openssh-server will be installed if not null
    example: "/root/.ssh/authorized_keys"
    """
    authorized_keys = fields.Nullable(fields.String())

    """
    strace the leapp upgrade service to this file ("" to disable)
    example: "/var/lib/leapp/upgrade.strace"
    """
    strace = fields.Nullable(fields.String())


class LiveModeRequirementsTasks(Model):
    topic = TransactionTopic

    """
    packages to be installed in the target userspace
    """
    packages = fields.List(fields.String())


class LiveImagePreparationInfo(Model):
    """
    Information about how the upgrade live image is set up.
    """
    topic = BootPrepTopic

    is_console_set_up = fields.Boolean(default=False)
    has_passwordless_root = fields.Boolean(default=False)
    has_sshd = fields.Boolean(default=False)


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
    kernel = fields.Nullable(fields.String())
    initramfs = fields.Nullable(fields.String())
    squashfs = fields.Nullable(fields.String())
