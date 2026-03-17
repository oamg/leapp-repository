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

    updated_config_location = fields.String()
    """ Location of the updated config that should be propagated to the source system. """

    target_path = fields.String()
    """ Location where should be the updated config placed. """


class MultipathConfigUpdatesInfo(Model):
    """ Aggregate information about multipath configs that were updated. """
    topic = SystemInfoTopic

    updates = fields.List(fields.Model(UpdatedMultipathConfig), default=[])
    """ Collection of multipath config updates that must be performed during the upgrade. """
