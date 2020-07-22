from leapp.actors import Actor
from leapp.libraries.actor.excluderepositories import process
from leapp.models import (
    CustomTargetRepository,
    RepositoriesExcluded,
    RepositoriesFacts,
    RepositoriesMap,
)
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ExcludeRepositories(Actor):
    """Generate list of repository IDs that should be ignored by Leapp during upgrade process."""

    name = "exclude_repositories"
    consumes = (RepositoriesFacts, RepositoriesMap, CustomTargetRepository)
    produces = (RepositoriesExcluded, Report)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        process()
