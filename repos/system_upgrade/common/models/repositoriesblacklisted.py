from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class RepositoriesBlacklisted(Model):
    """
    Repositories ID that should be ignored by Leapp during upgrade process
    """
    topic = SystemFactsTopic

    repoids = fields.List(fields.String(), default=[])
