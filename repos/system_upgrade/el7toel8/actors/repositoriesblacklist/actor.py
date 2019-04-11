from leapp.actors import Actor
from leapp.models import RepositoriesBlacklisted
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class RepositoriesBlacklist(Actor):
    """
    Generate list of Repositories ID that should be ignored by Leapp during upgrade process
    """

    name = 'repositories_blacklist'
    consumes = ()
    produces = (RepositoriesBlacklisted,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        self.produce(RepositoriesBlacklisted(
            repoids=[
                'rhel8-buildroot',  # As seem at PES Events
                'rhel8-crb',  # As seem at PES Events
                'codeready-builder-for-rhel-8-x86_64-rpms']))
