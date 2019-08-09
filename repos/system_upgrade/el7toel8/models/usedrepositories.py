from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class UsedRepository(Model):
    """
    List of packages installed from a specific repository.
    """

    topic = SystemInfoTopic

    repoid = fields.String()
    packages = fields.List(fields.String(), default=[])


class UsedRepositories(Model):
    """
    List of used repositories on the current system.
    """

    topic = SystemInfoTopic

    repositories = fields.List(fields.Model(UsedRepository), default=[])
