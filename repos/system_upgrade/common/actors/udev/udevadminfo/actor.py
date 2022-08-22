from leapp.actors import Actor
from leapp.libraries.stdlib import run
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
        out = run(['udevadm', 'info', '-e'])['stdout']
        self.produce(UdevAdmInfoData(db=out))
