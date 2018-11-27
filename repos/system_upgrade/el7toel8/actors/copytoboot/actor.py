from leapp.actors import Actor
from leapp.libraries.actor.library import copy_to_boot
from leapp.models import BootContent
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class CopyToBoot(Actor):
    name = 'copy_to_boot'
    description = 'Copy initramfs, which was specially prepared for the upgrade, together with its kernel to /boot/.'
    consumes = ()
    produces = (BootContent,)
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        copy_to_boot()
