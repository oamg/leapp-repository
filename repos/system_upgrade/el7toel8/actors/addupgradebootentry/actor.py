from leapp.actors import Actor
from leapp.libraries.actor.library import add_boot_entry
from leapp.models import BootContent
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class AddUpgradeBootEntry(Actor):
    name = 'add_upgrade_boot_entry'
    description = '''
        Add new boot entry for the leapp-provided initramfs so that leapp can continue with the upgrade
        process in the initramfs after reboot.
    '''

    consumes = (BootContent,)
    produces = ()
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        add_boot_entry()
