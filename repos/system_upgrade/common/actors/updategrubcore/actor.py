from leapp.actors import Actor
from leapp.libraries.actor import updategrubcore
from leapp.models import FirmwareFacts, TransactionCompleted
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class UpdateGrubCore(Actor):
    """
    Update GRUB2 core on legacy BIOS systems.

    On legacy (BIOS) systems, GRUB core (located in the gap between the MBR and the
    first partition), does not get automatically updated when GRUB is upgraded.
    """

    name = 'update_grub_core'
    consumes = (TransactionCompleted, FirmwareFacts)
    produces = (Report,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        updategrubcore.process()
