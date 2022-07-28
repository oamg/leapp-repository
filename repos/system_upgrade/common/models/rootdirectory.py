from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class RootSubdirectory(Model):
    """
    Representation of a single root subdirectory. Can be expanded as needed.
    """
    topic = SystemFactsTopic
    name = fields.String()
    target = fields.Nullable(fields.String())  # if it's a link


class InvalidRootSubdirectory(Model):
    """
    Representation of a single root subdirectory with non-utf name that is stored as a Blob.
    """
    topic = SystemFactsTopic
    name = fields.Blob()
    target = fields.Nullable(fields.Blob())


class RootDirectory(Model):
    topic = SystemFactsTopic
    items = fields.List(fields.Model(RootSubdirectory))  # should not be empty
    invalid_items = fields.Nullable(fields.List(fields.Model(InvalidRootSubdirectory)))
