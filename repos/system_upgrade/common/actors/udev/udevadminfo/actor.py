from leapp.actors import Actor
from leapp.libraries.actor import udevadminfo
from leapp.models import UdevAdmInfoData
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class UdevAdmInfo(Actor):
    """
    Produces data exported by the "udevadm info" command.
    """

    name = 'udevadm_info'
    consumes = ()
    produces = (UdevAdmInfoData,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        udevadminfo.process()
