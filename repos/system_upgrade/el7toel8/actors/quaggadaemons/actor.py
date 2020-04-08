from leapp.actors import Actor
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.models import InstalledRedHatSignedRPM, QuaggaToFrrFacts
from leapp.libraries.common.rpms import has_package
from leapp.libraries.actor.library import process_daemons

class QuaggaDaemons(Actor):
    """
    Checking for daemons that are currently running in the system.
    The tools will check for config files later on since these should stay in the system.
    """

    name = 'quagga_daemons'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (QuaggaToFrrFacts, )
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRedHatSignedRPM, 'quagga'):
            self.produce(process_daemons())
