from leapp.actors import Actor
from leapp.libraries.actor.quaggatofrr import process_facts
from leapp.models import QuaggaToFrrFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class QuaggaToFrr(Actor):
    """
    Edit frr configuration on the new system.

    Take gathered info about quagga from RHEL 7 and apply these to frr in RHEL 8.
    """

    name = 'quagga_to_frr'
    consumes = (QuaggaToFrrFacts, )
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        quagga_facts = next(self.consume(QuaggaToFrrFacts), None)

        if quagga_facts:
            process_facts(quagga_facts)
