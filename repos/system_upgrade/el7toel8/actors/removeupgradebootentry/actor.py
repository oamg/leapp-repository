from leapp.actors import Actor
from leapp.libraries.actor.library import remove_boot_entry
from leapp.models import BootContent
from leapp.tags import InitRamStartPhaseTag, IPUWorkflowTag


class RemoveUpgradeBootEntry(Actor):
    name = 'remove_upgrade_boot_entry'
    description = 'Remove the boot entry added by Leapp.'
    consumes = (BootContent,)
    produces = ()
    tags = (IPUWorkflowTag, InitRamStartPhaseTag)

    def process(self):
        remove_boot_entry()
