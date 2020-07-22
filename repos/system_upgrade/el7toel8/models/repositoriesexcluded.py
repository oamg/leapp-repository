from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic
from leapp.utils.deprecation import deprecated


class RepositoriesExcluded(Model):
    """Repositories ID that should be ignored by Leapp during upgrade process."""

    topic = SystemFactsTopic

    repoids = fields.List(fields.String(), default=[])


@deprecated(
    since="2020-10-01", message="Please use RepositoriesExcluded instead"
)
class RepositoriesBlacklisted(RepositoriesExcluded):
    pass
