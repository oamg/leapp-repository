from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class BootEntry(Model):
    """
    One entry in the boot loader configuration.

    Not meant to be produced directly, only as a part of :class:`SourceBootLoaderConfiguration`.
    """
    topic = SystemInfoTopic

    title = fields.String()
    """Title of the boot entry."""


class SourceBootLoaderConfiguration(Model):
    """Describes the bootloader configuration found on the source system."""
    topic = SystemInfoTopic

    entries = fields.List(fields.Model(BootEntry))
    """Boot entries available in the bootloader configuration."""
