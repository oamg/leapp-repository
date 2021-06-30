from leapp.models import Model, fields
from leapp.topics import TransactionTopic


class RepositoryMap(Model):
    """
    Mapping between repositories to be used during upgrade.

    Mapping of current system repository to target system version repositories to determine which
    ones should be enabled for the correct upgrade process.
    """

    topic = TransactionTopic

    from_repoid = fields.String()
    """source RHEL repoid as present in the Red Hat CDN"""
    to_repoid = fields.String()
    """target RHEL repoid as present in the Red Hat CDN"""
    to_pes_repo = fields.String()
    """target RHEL repo name as used in the Package Evolution Service database"""
    from_minor_version = fields.String()
    """To which source RHEL minor versions the mapping relates to"""
    to_minor_version = fields.String()
    """To which target RHEL minor versions the mapping relates to"""
    arch = fields.String()
    """CPU architecture the mapping relates to"""
    repo_type = fields.StringEnum(choices=['rpm', 'srpm', 'debuginfo'])
    """Type of content the mapped repos hold"""


class RepositoriesMap(Model):
    topic = TransactionTopic

    repositories = fields.List(fields.Model(RepositoryMap), default=[])
    """List of source RHEL repo <-> target RHEL repo mappings"""
