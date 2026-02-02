from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import grub
from leapp.libraries.common.config import architecture
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
        if architecture.matches_architecture(architecture.ARCH_S390X):
            return

        try:
            devices = grub.get_grub_devices()
        except grub.GRUBDeviceError as err:
            # TODO(pstodulk): Tests missing
            raise StopActorExecutionError(
                message='Cannot detect GRUB devices',
                details={'details': str(err)}
            )
        grub_info = GrubInfo(orig_devices=devices)
        grub_info.orig_device_name = devices[0] if len(devices) == 1 else None
        self.produce(grub_info)
