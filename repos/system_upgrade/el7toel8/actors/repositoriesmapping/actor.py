from leapp.actors import Actor
from leapp.libraries.actor.repositoriesmapping import scan_repositories
from leapp.models import RepositoriesMap
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RepositoriesMapping(Actor):
    """
    Produces message containing repository mapping based on provided file.
    """

    name = 'repository_mapping'
    consumes = ()
    produces = (RepositoriesMap,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scan_repositories()
