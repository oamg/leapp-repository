from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class FstabContents(Model):
    topic = SystemFactsTopic

    lines = fields.List(fields.String())


class ModifiedFstabContents(FstabContents):
    pass
