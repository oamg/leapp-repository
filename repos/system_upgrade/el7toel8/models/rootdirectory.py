from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class RootSubdirectory(Model):
    """
    Representation of a single root subdirectory. Can be expanded as needed.
    """
    topic = SystemFactsTopic
    name = fields.String()
    target = fields.Nullable(fields.String())  # if it's a link


class RootDirectory(Model):
    topic = SystemFactsTopic
    items = fields.List(fields.Model(RootSubdirectory))  # should not be empty
