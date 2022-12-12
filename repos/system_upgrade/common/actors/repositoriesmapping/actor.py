from leapp.actors import Actor
from leapp.libraries.actor.repositoriesmapping import scan_repositories
from leapp.models import ConsumedDataAsset, RepositoriesMapping
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RepositoriesMappingScanner(Actor):
    """
    Produces message containing repository mapping based on provided file.

    The actor filters out data irrelevant to the current IPU (data with different
    source/target major versions) from the raw repository mapping data.
    """

    name = 'repository_mapping'
    consumes = ()
    produces = (ConsumedDataAsset, RepositoriesMapping,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scan_repositories()
