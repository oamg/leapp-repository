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


@deprecated(
    since='2026-06-01',
    message=(
        'This model has been deprecated and replaced. '
        'To get the list of blocklisted repositories, use RepositoriesBlocklisted. '
        'To request a repository to be blocklisted, use RepositoriesSetupTasks.blocklist.'
    ),
)
class RepositoriesBlacklisted(RepositoriesBlocklisted):
    """
    Repository IDs that should be ignored by Leapp during the upgrade process.
    """
    topic = SystemFactsTopic
