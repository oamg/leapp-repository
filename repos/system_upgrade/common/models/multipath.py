from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class MultipathInfo(Model):
    """ Available information about multpath devices of the source system. """
    topic = SystemInfoTopic

    is_configured = fields.Boolean(default=False)
    """
    True if multipath is configured on the system.

    Detected based on checking whether /etc/multipath.conf exists.
    """

    config_dir = fields.Nullable(fields.String())
    """ Value of config_dir in the defaults section. None if not set. """


class UpdatedMultipathConfig(Model):
    """ Information about multipath config that needed to be modified for the target system. """
    topic = SystemInfoTopic

    path = fields.String()
