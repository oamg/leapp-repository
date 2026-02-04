from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import grub
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import GrubInfo


def process():
    if architecture.matches_architecture(architecture.ARCH_S390X):
        return

    try:
        devices = grub.get_grub_devices()
    except grub.GRUBDeviceError as err:
        raise StopActorExecutionError(
            message='Cannot detect GRUB devices',
            details={'details': str(err)}
        )

    grub_info = GrubInfo(orig_devices=devices)
    grub_info.orig_device_name = devices[0] if len(devices) == 1 else None
    api.produce(grub_info)
