from leapp.actors import Actor
from leapp.libraries.actor import scannvme
from leapp.models import NVMEInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanNVMe(Actor):
    """
    Detect existing NVMe devices.

    The detection is performed by checking content under /sys/class/nvme/
    directory where all NVMe devices should be listed. Additional information
    is collected from the present files under each specific device.

    Namely the NVMe transport type and the device name is collected at this
    moment.
    """

    name = 'scan_nvme'
    consumes = ()
    produces = (NVMEInfo,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scannvme.process()
