from leapp.actors import Actor
from leapp.libraries.actor.quaggadaemons import process_daemons
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM, QuaggaToFrrFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class QuaggaDaemons(Actor):
    """
    Active quagga daemons check.

    Checking for daemons that are currently running in the system.
    These should be enabled in /etc/frr/daemons later in the process.
    The tools will check for config files later on since these should stay in the system.
    """

    name = 'quagga_daemons'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (QuaggaToFrrFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRedHatSignedRPM, 'quagga'):
            self.produce(process_daemons())
