from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class RaidInfo(Model):
    """Information about RAID usage on the source system."""
    topic = SystemInfoTopic

    dmraid_used = fields.Boolean(default=False)
    """Whether dmraid (device-mapper RAID / fake RAID) is in use."""

    mdraid_used = fields.Boolean(default=False)
    """Whether mdadm software RAID is in use."""
