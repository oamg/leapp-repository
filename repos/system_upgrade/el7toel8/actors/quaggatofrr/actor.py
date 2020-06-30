from leapp.actors import Actor
from leapp.models import QuaggaToFrrFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag
from leapp.libraries.actor.quaggatofrr import process_facts


class QuaggaToFrr(Actor):
    """
    Move configuration from quagga format to the new format in FRR
    """

    name = 'quagga_to_frr'
    consumes = (QuaggaToFrrFacts, )
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        quagga_facts = next(self.consume(QuaggaToFrrFacts))

        if quagga_facts:
            process_facts(quagga_facts)
