from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class DefaultSourceBootEntry(Model):
    """ Default boot entry of the source system. """
    topic = SystemInfoTopic

    initramfs_path = fields.String()
    kernel_path = fields.String()
