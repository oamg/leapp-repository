from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class YumConfig(Model):
    topic = SystemFactsTopic

    enabled_plugins = fields.List(fields.String(), default=[])
