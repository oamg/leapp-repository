from leapp.actors import Actor
from leapp.libraries.common import grub
from leapp.libraries.common.config import architecture
from leapp.models import GrubInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanGrubDeviceName(Actor):
    """
    Find the name of the block device where GRUB is located
    """

    name = 'scan_grub_device_name'
    consumes = ()
    produces = (GrubInfo,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        if architecture.matches_architecture(architecture.ARCH_S390X):
            return

        device_name = grub.get_grub_device()
        if device_name:
            self.produce(GrubInfo(orig_device_name=device_name))
        else:
            self.produce(GrubInfo())
