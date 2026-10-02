from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class RepositoryData(Model):
    topic = SystemFactsTopic

    repoid = fields.String()
    name = fields.String()
    baseurl = fields.Nullable(fields.String())
    metalink = fields.Nullable(fields.String())
    mirrorlist = fields.Nullable(fields.String())
    enabled = fields.Boolean(default=True)
    additional_fields = fields.Nullable(fields.String())
    proxy = fields.Nullable(fields.String())


class RepositoryFile(Model):
    topic = SystemFactsTopic

    file = fields.String()
    data = fields.List(fields.Model(RepositoryData))


class RepositoriesFacts(Model):
    topic = SystemFactsTopic

    repositories = fields.List(fields.Model(RepositoryFile))


class RepositoriesFactsTarget(RepositoriesFacts):
    """
    A point-in-time snapshot of the ``.repo`` files parsed from the build
    (scratch) container after the target userspace has been created.

    Produced by ``targetuserspacecreator`` and consumed by exactly two actors,
    both in the later ``TargetTransactionChecks`` phase: ``adjustlocalrepos``
    (reads each repofile's ``file``, ``repoid``, ``baseurl``, ``mirrorlist``)
    and ``missinggpgkeysinhibitor`` (reads ``repoid`` and the gpg-key fields).

    Sharing the parsed result as a message lets each consumer obtain the target
    repo metadata without re-implementing repofile discovery/parsing, and
    decouples them from each other and from the producing actor's internals.
    Being a *produced* message, leapp persists it as a durable record of the
    freshly-built container's repo state, useful for diagnostics/sosreports.

    It carries the *target* container's repos. It is intentionally kept a
    distinct type from the source-system ``RepositoriesFacts`` (same field
    shape, different subject and lifecycle) to prevent the two being conflated.
    """

