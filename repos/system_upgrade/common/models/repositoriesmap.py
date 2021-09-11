from leapp.models import Model, fields
from leapp.topics import TransactionTopic


class RepoMapEntry(Model):
    topic = TransactionTopic

    source = fields.String()
    """The source PES id."""

    target = fields.List(fields.String())
    """List of target PES ids"""


class PESIDRepositoryEntry(Model):
    """
    Represent metadata about particular repository.

    The metadata are used to identify purpose and nature of the repository.

    Warning: This model is not expected to be consumed/produced by any actor
    directly. As well, it is not covered by deprecation process and can be
    changed or removed any time.
    """

    topic = TransactionTopic

    pesid = fields.String()
    """
    The PES id of the repository.

    The PES id indicate family of YUM repositories. E.g. rhel8-BaseOS covers
    variants of BaseOS YUM repositories for all channels, architectures,
    RHUI, etc, which have basically same purpose.
    """

    major_version = fields.String()
    """
    The major version of OS.

    E.g. for RHEL 7.9 the major version is 7. Since we work with versions
    as with strings throughout the whole codebase, we keep this data type here too.
    """

    repoid = fields.String()
    """
    The repository ID which identifies the repository from YUM/DNF POV.
    """

    arch = fields.StringEnum(['x86_64', 's390x', 'ppc64le', 'aarch64'])
    """
    The architecture for which the repository is delivered.
    """

    repo_type = fields.StringEnum(['rpm', 'debug', 'srpm'])
    """
    The repository type.

    In our case, we usually map just repositories with the 'rpm' type, so
    usually you can see just this one, but the others are possible to add
    too.
    """

    channel = fields.StringEnum(['ga', 'tuv', 'e4s', 'eus', 'aus', 'beta'])
    """
    The 'channel' of the repository.

    The 'channel' could be a little bit inaccurate term, but let's use it in
    this project. The standard repositories has 'ga' channel. 'beta'
    repositories are unsupported for IPU, however they are useful for testing
    purposes. The other channels indicate premium repositories.
    """

    rhui = fields.StringEnum(['', 'aws', 'azure'])
    """
    Indicate whether the repository is deliver for RHUI and which one.

    For non-rhui systems: empty string
    For AWS or Azure: 'aws' / 'azure'
    """


class RepositoriesMapping(Model):
    """
    Private model containing information about mapping between repositories.

    Warning: We expect to be only consumers of this model.
    This means the model is not covered by deprecation process and can be
    changed or removed any time.
    """
    topic = TransactionTopic

    mapping = fields.List(fields.Model(RepoMapEntry), default=[])
    repositories = fields.List(fields.Model(PESIDRepositoryEntry), default=[])
