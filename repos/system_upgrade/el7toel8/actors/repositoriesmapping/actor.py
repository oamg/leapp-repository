from leapp.actors import Actor
from leapp.libraries.actor.library import scan_repositories
from leapp.models import RepositoriesMap
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class RepositoriesMapping(Actor):
    """
    Produces message containing repository mapping based on provided file.
    """

    name = 'repository_mapping'
    consumes = ()
    produces = (RepositoriesMap, Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        scan_repositories('/etc/leapp/files/repomap.csv')
