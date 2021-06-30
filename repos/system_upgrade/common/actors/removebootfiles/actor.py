from leapp.actors import Actor
from leapp.libraries.actor.removebootfiles import remove_boot_files
from leapp.models import BootContent
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class RemoveBootFiles(Actor):
    """
    Remove Leapp provided initramfs from boot partition.

    Since Leapp provided initramfs and kernel are already loaded into RAM at this phase, remove
    them to have as little space requirements for boot partition as possible.
    """

    name = 'remove_boot_files'
    consumes = (BootContent,)
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        remove_boot_files()
