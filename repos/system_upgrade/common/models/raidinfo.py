from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class MDArray(Model):
    """Information about a single mdadm software RAID array."""

    topic = SystemInfoTopic

    UUID = fields.String()
    """UUID of the mdadm array."""


class RaidInfo(Model):
    """Information about RAID usage on the source system."""
    topic = SystemInfoTopic

    dmraid_used = fields.Boolean(default=False)
    """Whether dmraid (device-mapper RAID / fake RAID) is in use."""

    md_arrays = fields.List(fields.Model(MDArray), default=[])
    """List of active mdadm software RAID arrays."""
