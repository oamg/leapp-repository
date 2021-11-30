from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class UsedRepository(Model):
    """
    Describe list of current packages installed from a specific repository
    """

    topic = SystemInfoTopic

    repository = fields.String()
    packages = fields.List(fields.String(), default=[])


class UsedRepositories(Model):
    """
    Describe list of used repositories in the current system
    """

    topic = SystemInfoTopic

    repositories = fields.List(fields.Model(UsedRepository), default=[])
