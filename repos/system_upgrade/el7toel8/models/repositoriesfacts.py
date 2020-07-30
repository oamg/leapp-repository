from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class RepositoryData(Model):
    topic = SystemFactsTopic

    repoid = fields.String()
    name = fields.String()
    baseurl = fields.Nullable(fields.String())
    metalink = fields.Nullable(fields.String())
    mirrorlist = fields.Nullable(fields.String())
    enabled = fields.Boolean(default=True)
    additional_fields = fields.Nullable(fields.String())


class RepositoryFile(Model):
    topic = SystemFactsTopic

    file = fields.String()
    data = fields.List(fields.Model(RepositoryData))


class RepositoriesFacts(Model):
    topic = SystemFactsTopic

    repositories = fields.List(fields.Model(RepositoryFile))

class TMPTargetRepositoriesFacts(RepositoriesFacts):
    """
    Do not consume this model anywhere outside of localreposinhibit

    The model is temporary and will be removed in close future
    """
    pass
