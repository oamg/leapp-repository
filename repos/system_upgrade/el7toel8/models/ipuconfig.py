from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class EnvVar(Model):
    topic = SystemInfoTopic

    name = fields.String()
    value = fields.String()


class IPUConfig(Model):
    """
    IPU workflow configuration model
    """
    topic = SystemInfoTopic

    leapp_env_vars = fields.List(fields.Model(EnvVar), default=[])
