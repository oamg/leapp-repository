from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class CephInfo(Model):
    topic = SystemInfoTopic

    encrypted_volumes = fields.List(fields.String(), default=[])
