from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class MultipathConfig9to10(Model):
    """
    Model information about multipath configuration file important for the 9>10 upgrade path.
    """
    topic = SystemInfoTopic

    pathname = fields.String()
    """Config file path name"""

    config_dir = fields.Nullable(fields.String())
    """
    Value of config_dir in the defaults section. None if not set.
    Used both to track config lines that need commenting out and
    to determine the actual directory location.
    """

    bindings_file = fields.Nullable(fields.String())
    """
    Value of bindings_file in the defaults section. None if not set.
    Used both to track config lines that need commenting out and
    to determine the actual file location for copying.
    """

    wwids_file = fields.Nullable(fields.String())
    """
    Value of wwids_file in the defaults section. None if not set.
    Used both to track config lines that need commenting out and
    to determine the actual file location for copying.
    """

    prkeys_file = fields.Nullable(fields.String())
    """
    Value of prkeys_file in the defaults section. None if not set.
    Used both to track config lines that need commenting out and
    to determine the actual file location for copying.
    """

    has_socket_activation = fields.Boolean(default=True)
    """True if multipathd socket activation is enabled"""

    has_dm_nvme_multipathing = fields.Boolean(default=False)
    """True if DM NVMe multipathing is enabled"""

    has_getuid = fields.Boolean(default=False)
    """True if the getuid option is set anywhere in the multipath config"""


class MultipathConfFacts9to10(Model):
    """
    Model representing information from multipath configuration files important for the 9>10 upgrade path.
    """
    topic = SystemInfoTopic

    configs = fields.List(fields.Model(MultipathConfig9to10), default=[])
    """List of multipath configuration files"""
