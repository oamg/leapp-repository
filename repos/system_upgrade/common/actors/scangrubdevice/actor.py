from leapp.actors import Actor
from leapp.libraries.actor import scangrubdevice
from leapp.models import GrubInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanGrubDeviceName(Actor):
    """
    Find the name of the block devices where GRUB is located
    """

    name = 'scan_grub_device_name'
    consumes = ()
    produces = (GrubInfo,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scangrubdevice.process()
