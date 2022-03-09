from leapp.actors import Actor
from leapp.libraries.actor.nisscan import NISScanLibrary
from leapp.models import NISConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class NISScanner(Actor):
    """
    Collect information about the NIS packages configuration.
    """

    name = 'nis_scanner'
    consumes = ()
    produces = (NISConfig,)
    tags = (FactsPhaseTag, IPUWorkflowTag,)

    def process(self):
        NISScanLibrary().process()
