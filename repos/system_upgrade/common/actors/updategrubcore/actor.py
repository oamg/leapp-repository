from leapp.actors import Actor
from leapp.libraries.actor.updategrubcore import update_grub_core
from leapp.libraries.common import grub
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts, TransactionCompleted
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class UpdateGrubCore(Actor):
    """
    On legacy (BIOS) systems, GRUB core (located in the gap between the MBR and the
    first partition), does not get automatically updated when GRUB is upgraded.
    """

    name = 'update_grub_core'
    consumes = (TransactionCompleted, FirmwareFacts)
    produces = (Report,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        ff = next(self.consume(FirmwareFacts), None)
        if ff and ff.firmware == 'bios':
            grub_dev = grub.get_grub_device()
            if grub_dev:
                update_grub_core(grub_dev)
            else:
                api.current_logger().warning('Leapp could not detect GRUB on {}'.format(grub_dev))
