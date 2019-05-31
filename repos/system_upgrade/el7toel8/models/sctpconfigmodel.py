from leapp.models import Model, fields
from leapp.topics import SCTPConfigTopic


class SCTPConfig(Model):
    topic = SCTPConfigTopic
    wanted = fields.Boolean(default=False)
