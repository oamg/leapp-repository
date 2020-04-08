from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.models import CustomTargetRepository
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanCLIenablrepo(Actor):
    """
    Produce CustomTargetRepository based on the LEAPP_ENABLE_REPOS in config.
    """

    name = 'scanclienablerepo'
    consumes = ()
    produces = (CustomTargetRepository)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        library.process()
