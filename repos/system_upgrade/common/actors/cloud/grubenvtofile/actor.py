from leapp.actors import Actor
from leapp.libraries.actor.grubenvtofile import grubenv_to_file
from leapp.models import HybridImage
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class GrubenvToFile(Actor):
    """
    Convert "grubenv" symlink to a regular file on Azure hybrid images using BIOS.

    Azure images provided by Red Hat aim for hybrid (BIOS/EFI) functionality,
    however, currently GRUB is not able to see the "grubenv" file if it is a symlink
    to a different partition (default on EFI with grub2-efi pkg installed) and
    fails on BIOS systems. This actor converts the symlink to the normal file
    with the content of grubenv on the EFI partition in case the system is using BIOS
    and running on the Azure cloud. This action is reported in the preupgrade phase.
    """

    name = 'grubenvtofile'
    consumes = (HybridImage,)
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        grubenv_msg = next(self.consume(HybridImage), None)

        if grubenv_msg and grubenv_msg.detected:
            grubenv_to_file()
