from leapp.actors import Actor
from leapp.libraries.actor import checkifcfg_ifcfg as ifcfg
from leapp.models import IfCfg, InstalledRPM, Report, RpmTransactionTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckIfcfg(Actor):
    """
    Ensures that ifcfg files are compatible with NetworkManager

    Checks whether the ifcfg files would work with NetworkManager's ifcfg-rh
    compatibility module -- they are of known type, well-formed and not
    explicitly disabled with NM_CONTROLLED=no.

    Makes sure relevant NetworkManager modules end up getting installed.
    """

    name = "check_ifcfg"
    consumes = (IfCfg, InstalledRPM,)
    produces = (Report, RpmTransactionTasks,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        ifcfg.process()
