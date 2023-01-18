from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic
from leapp.utils.deprecation import deprecated


class RepositoryData(Model):
    topic = SystemFactsTopic

    repoid = fields.String()
    """
    Unique identifier for the repository.
    """
    name = fields.String()
    """
    Display name of the repository.
    """
    baseurl = fields.Nullable(fields.String())
    """
    URL where the repository data is located, possibly missing if there's a meta link or mirror list.
    """
    metalink = fields.Nullable(fields.String())
    """
    See documentation for repository files.
    """
    mirrorlist = fields.Nullable(fields.String())
    """
    See documentation for repository files.
    """
    enabled = fields.Boolean(default=True)
    """
    Is this repository enabled?
    """
    additional_fields = fields.Nullable(fields.String())
    """
    See documentation for repository files.
    """
    proxy = fields.Nullable(fields.String())
    """
    Proxy URL necessary for this repository
    """
    # TODO: Remove default
    file = fields.String(default='')
    """
    The repository file where this repo was defined
    """
    # TODO: Remove default
    kind = fields.StringEnum(choices=['custom', 'rhui', 'rhsm'], default='custom')
    """
    Declares if this comes through RHSM, RHUI or from a custom repo file.
    """


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
