from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class FIPSFacts(Model):
    topic = SystemFactsTopic

    enabled = fields.Boolean()
