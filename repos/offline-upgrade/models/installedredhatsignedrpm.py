from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class RedHatSignedRPM(Model):
    topic = SystemInfoTopic
    name = fields.String(required=True)
    epoch = fields.String(required=True)
    version = fields.String(required=True)
    release = fields.String(required=True)
    arch = fields.String(required=True)
    pgpsig = fields.String(required=True)


class InstalledRedHatSignedRPM(Model):
    topic = SystemInfoTopic
    items = fields.List(fields.Model(RedHatSignedRPM), required=True, default=[])
