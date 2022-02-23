from leapp.actors import Actor
from leapp.libraries.actor import checkifcfg_ifcfg as ifcfg
from leapp.models import InstalledRPM, Report, RpmTransactionTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class CheckIfcfg(Actor):
    """
    Ensures that ifcfg files are compatible with NetworkManager

    Checks whether the ifcfg files would work with NetworkManager's ifcfg-rh
    compatibility module -- they are of known type, well-formed and not
    explicitly disabled with NM_CONTROLLED=no.

    Makes sure relevant NetworkManager modules end up getting installed.
    """

    name = "check_ifcfg"
    consumes = (InstalledRPM,)
    produces = (Report, RpmTransactionTasks,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        ifcfg.process()
