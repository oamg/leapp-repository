from leapp.actors import Actor
from leapp.libraries.actor.library import copy_to_boot
from leapp.models import BootContent
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class CopyToBoot(Actor):
    """
    Copy Leapp provided initramfs to boot partition.

    In order to execute upgrade, Leapp provides a special initramfs and kernel to be used during
    the process. Such artifacts need to be placed inside boot partition.
    """

    name = 'copy_to_boot'
    consumes = ()
    produces = (BootContent,)
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        copy_to_boot()
