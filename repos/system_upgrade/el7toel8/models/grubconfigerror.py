from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class GrubConfigError(Model):
    topic = SystemFactsTopic

    error_detected = fields.Boolean(default=False)
