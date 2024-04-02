from leapp.actors import Actor
from leapp.libraries.actor import scan_layout as scan_layout_lib
from leapp.models import GRUBDevicePartitionLayout, GrubInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanGRUBDevicePartitionLayout(Actor):
    """
    Scan all identified GRUB devices for their partition layout.
    """

    name = 'scan_grub_device_partition_layout'
    consumes = (GrubInfo,)
    produces = (GRUBDevicePartitionLayout,)
    tags = (FactsPhaseTag, IPUWorkflowTag,)

    def process(self):
        scan_layout_lib.scan_grub_device_partition_layout()
