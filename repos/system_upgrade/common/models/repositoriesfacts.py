from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic
from leapp.utils.deprecation import deprecated


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


@deprecated(
    since="2020-09-01",
    message=(
        "The model is temporary and not assumed to be used in any "
        "other actors."
    ),
)
class TMPTargetRepositoriesFacts(RepositoriesFacts):
    """Do not consume this model anywhere outside of localreposinhibit.

    The model is temporary and will be removed in close future
    """

    pass
