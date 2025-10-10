from leapp.models import fields, Model
from leapp.reporting import deprecated
from leapp.topics import TransactionTopic


class TargetRepositoryBase(Model):
    topic = TransactionTopic
    repoid = fields.String()


class UsedTargetRepository(TargetRepositoryBase):
    pass


@deprecated(
    since="2025-07-23",
    message="This model is deprecated, use DistroTargetRepository instead.",
)
class RHELTargetRepository(TargetRepositoryBase):
    pass


class DistroTargetRepository(TargetRepositoryBase):
    pass


class CustomTargetRepository(TargetRepositoryBase):
    name = fields.Nullable(fields.String())
    baseurl = fields.Nullable(fields.String())
    enabled = fields.Boolean(default=True)


class TargetRepositories(Model):
    """
    Repositories supposed to be used during the IPU process

    The list of the actually used repositories could be just subset
    of these repositories. In case of `custom_repositories`, all such repositories
    must be available otherwise the upgrade is inhibited. But in case of
    `distro_repos`, only BaseOS and Appstream repos are required now. If others
    are missing, upgrade can still continue.

    Note: `rhel_repos` are deprecated, use `distro_repos` instead.
    """
    topic = TransactionTopic

    # DEPRECATED: this has been superseded by distro_repos
    rhel_repos = fields.List(fields.Model(RHELTargetRepository))
    """
    Expected target YUM RHEL repositories provided via RHSM

    DEPRECATED - use distro_repos instead.

    These repositories are stored inside /etc/yum.repos.d/redhat.repo and
    are expected to be used based on the provided repositories mapping.
    """

    distro_repos = fields.List(fields.Model(DistroTargetRepository))
    """
    Expected target DNF repositories provided by the distribution.

    On RHEL these are the repositories provided via RHSM.
    These repositories are stored inside /etc/yum.repos.d/redhat.repo and
    are expected to be used based on the provided repositories mapping.

    On other distributions, such as Centos Stream these are repositories
    in /etc/yum.repos.d/ that are provided by the distribution and are expected
    to be used based on the provided repositories mapping.
    """

    custom_repos = fields.List(fields.Model(CustomTargetRepository), default=[])
    """
    Custom YUM repositories required to be used for the IPU

    Usually contains third-party or custom repositories specified by user
    to be used for the IPU. But can contain also RHEL repositories. Difference
    is that these repositories are not mapped automatically but are explicitly
    required by user or by an additional product via actors.
    """


class UsedTargetRepositories(Model):
    """
    Repositories that are used for the IPU process

    This is the source of truth about the repositories used during the upgrade.
    Once specified, it is used for all actions related to the upgrade rpm
    transaction itself.
    """
    topic = TransactionTopic
    repos = fields.List(fields.Model(UsedTargetRepository))
    """
    The list of the used target repositories.
    """


class CustomTargetRepositoryFile(Model):
    topic = TransactionTopic
    file = fields.String()
