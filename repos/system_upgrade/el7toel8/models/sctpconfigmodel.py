from leapp.models import fields, Model
from leapp.topics import SCTPConfigTopic


class SCTPConfig(Model):
    topic = SCTPConfigTopic
    wanted = fields.Boolean(default=False)
