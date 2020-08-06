from leapp.actors import Actor
from leapp.libraries.actor.excluderepositories import process
from leapp.models import (
    RepositoriesBlacklisted,
    RepositoriesExcluded,
    RepositoriesFacts,
    RepositoriesMap,
)
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(RepositoriesBlacklisted)
class ExcludeRepositories(Actor):
    """Generate list of repository IDs that should be ignored by Leapp during upgrade process."""

    name = "exclude_repositories"
    consumes = (
        RepositoriesFacts,
        RepositoriesMap,
    )
    produces = (
        RepositoriesExcluded,
        RepositoriesBlacklisted,
        Report,
    )
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        process()
