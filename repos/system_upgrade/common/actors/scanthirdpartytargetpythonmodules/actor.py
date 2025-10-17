from leapp.actors import Actor
from leapp.libraries.actor import scanthirdpartytargetpythonmodules
from leapp.models import DistributionSignedRPM, ThirdPartyTargetPythonModules
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanThirdPartyTargetPythonModules(Actor):
    """
    Detect third-party target Python modules and RPMs on the source system.

    """

    name = 'scan_third_party_target_python_modules'
    consumes = (DistributionSignedRPM,)
    produces = (ThirdPartyTargetPythonModules,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scanthirdpartytargetpythonmodules.process()
