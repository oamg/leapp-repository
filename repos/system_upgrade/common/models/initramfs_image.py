from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class InitramfsInfo(Model):
    """ Information about an initramfs image """
    topic = SystemInfoTopic

    path = fields.String()
    used_dracut_modules = fields.List(fields.String(), default=[])


class DefaultInitramfsInfo(InitramfsInfo):
    pass
