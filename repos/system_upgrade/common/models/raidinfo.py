from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class MDArray(Model):
    """Information about a single mdadm software RAID array."""

    topic = SystemInfoTopic

    uuid = fields.String()
    """UUID of the mdadm array."""


class RAIDInfo(Model):
    """Information about RAID usage on the source system."""
    topic = SystemInfoTopic

    md_arrays = fields.List(fields.Model(MDArray), default=[])
    """List of active mdadm software RAID arrays."""
