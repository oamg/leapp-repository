from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic
from leapp.utils.deprecation import deprecated


class RepositoriesBlocklisted(Model):
    """
    Repository IDs that have been excluded from the target system during the upgrade.

    This message is expected to be produced just by one actor,
    but it can be consumed by others to check what repositories have been ignored
    during the upgrade process.
    """
    topic = SystemFactsTopic

    repoids = fields.List(fields.String(), default=[])
    """
    List of excluded (blocked) repository IDs.
    """


@deprecated(
    since='2026-06-01',
    message=(
        'This model has been deprecated and replaced. '
        'To get the list of blocklisted repositories, consume RepositoriesBlocklisted. '
        'To request a repository to be blocklisted, produce RepositoriesSetupTasks.to_block.'
    ),
)
class RepositoriesBlacklisted(RepositoriesBlocklisted):
    """
    Specify list of repository IDs that should be blocked during the upgrade.

    Note this is deprecated and you should use RepositoriesSetupTasks.to_block
    """
    topic = SystemFactsTopic
