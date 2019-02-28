from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class XFSPresence(Model):
    topic = SystemInfoTopic

    present = fields.Boolean(default=False)
    without_ftype = fields.Boolean(default=False)
