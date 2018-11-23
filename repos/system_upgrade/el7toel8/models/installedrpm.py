from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic

class RPM(Model):
    topic = SystemInfoTopic
    name = fields.String()
    epoch = fields.String()
    version = fields.String()
    release = fields.String()
    arch = fields.String()
    pgpsig = fields.String()


class InstalledRPM(Model):
    topic = SystemInfoTopic
    items = fields.List(fields.Model(RPM), default=[])
