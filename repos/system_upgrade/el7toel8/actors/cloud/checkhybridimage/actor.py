from leapp.actors import Actor
from leapp.models import InstalledRPM, HybridImage, FirmwareFacts
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.actor.checkhybridimage import check_hybrid_image


class CheckHybridImage(Actor):
    """
    Check if the system is using Azure hybrid image.

    These images have a default relative symlink to EFI
    partion even when booted using BIOS and in such cases
    GRUB is not able find "grubenv" to get the kernel cmdline
    options and fails to boot after upgrade`.
    """

    name = 'checkhybridimage'
    consumes = (InstalledRPM, FirmwareFacts)
    produces = (HybridImage,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        check_hybrid_image()
