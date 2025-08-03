from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class BootEntry(Model):
    """ Boot entry information."""
    topic = SystemInfoTopic

    initramfs_path = fields.String()
    kernel_path = fields.String()


class DefaultSourceBootEntry(BootEntry):
    """ Default boot entry of the source system. """
    pass
