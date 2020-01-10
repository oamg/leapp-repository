from leapp.actors import Actor
from leapp.libraries.actor.library import update_grub_core
from leapp.models import TransactionCompleted, UpdateGrub
from leapp.reporting import Report
from leapp.tags import RPMUpgradePhaseTag, IPUWorkflowTag


class UpdateGrubCore(Actor):
    """
    On legacy (BIOS) systems, GRUB core (located in the gap between the MBR and the
    first partition), does not get automatically updated when GRUB is upgraded.
    """

    name = 'update_grub_core'
    consumes = (TransactionCompleted, UpdateGrub)
    produces = (Report,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        dev = next(self.consume(UpdateGrub), None)
        if dev:
            update_grub_core(dev.grub_device)
