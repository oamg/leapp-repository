from leapp.models import fields, Model
from leapp.topics import TransactionTopic


class SkippedRepositories(Model):
    """
    Message that contains all skipped repositories and the packages that will not be upgraded as a result of those
    repositories being skipped.
    """
    topic = TransactionTopic
    repos = fields.List(fields.String(), default=[])
    """ List of repositories ids that are going to be skipped for the upgrade """
    packages = fields.List(fields.String(), default=[])
    """ List of packages that are not going to be upgraded because of skipped repositories """
