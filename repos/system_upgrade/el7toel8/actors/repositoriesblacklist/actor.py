from leapp.actors import Actor
from leapp.libraries.actor.library import process
from leapp.models import RepositoriesBlacklisted, RepositoriesFacts
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class RepositoriesBlacklist(Actor):
    """
    Generate list of repository IDs that should be ignored by Leapp during upgrade process
    """

    name = 'repositories_blacklist'
    consumes = (RepositoriesFacts,)
    produces = (RepositoriesBlacklisted,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        process()
