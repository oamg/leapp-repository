from leapp.models import Model, fields
from leapp.topics import TransactionTopic 

class RepositoryMap(Model):
    """
    Mapping between repositories to be used during upgrade.

    Mapping of current system repository to target system version repositories to determine which
    ones should be enabled for the correct upgrade process.
    """

    topic = TransactionTopic

    from_id = fields.String()
    to_id = fields.String()
    from_minor_version = fields.String()
    to_minor_version = fields.String()
    arch = fields.String()
    repo_type = fields.StringEnum(choices=['rpm', 'srpm', 'debuginfo'])


class RepositoriesMap(Model):
    topic = TransactionTopic

    repositories = fields.List(fields.Model(RepositoryMap), default=[])
