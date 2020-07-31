from leapp.actors import Actor
from leapp.libraries.actor.repositoriesblacklist import process
from leapp.models import RepositoriesBlacklisted, RepositoriesFacts, RepositoriesMap
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class RepositoriesBlacklist(Actor):
    """
    Generate list of repository IDs that should be ignored by Leapp during upgrade process
    """

    name = 'repositories_blacklist'
    consumes = (RepositoriesFacts, RepositoriesMap, )
    produces = (RepositoriesBlacklisted, Report)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        process()
