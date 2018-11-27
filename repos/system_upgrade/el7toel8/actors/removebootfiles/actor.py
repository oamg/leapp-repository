from leapp.actors import Actor
from leapp.libraries.actor.library import remove_boot_files
from leapp.models import BootContent
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class RemoveBootFiles(Actor):
    name = 'remove_boot_files'
    description = '''
        Remove the Leapp-provided kernel and initramfs as they are already loaded in RAM at this phase
        and we want to have as little space requirements for /boot as possible.
    '''
    consumes = (BootContent,)
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        remove_boot_files()
