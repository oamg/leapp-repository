from leapp.actors import Actor
from leapp.models import QuaggaToFrrFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import api
from leapp.libraries.actor.library import process_facts

class QuaggaToFrr(Actor):
    """
    No documentation has been provided for the quagga_to_frr actor.
    """

    name = 'quagga_to_frr'
    consumes = (QuaggaToFrrFacts, )
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        quagga_facts = next(self.consume(QuaggaToFrrFacts))

        if quagga_facts:
            process_facts(quagga_facts)
