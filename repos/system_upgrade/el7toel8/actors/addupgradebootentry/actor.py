from leapp.actors import Actor
from leapp.libraries.actor.library import add_boot_entry
from leapp.models import BootContent
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class AddUpgradeBootEntry(Actor):
    """
    Add new boot entry for Leapp provided initramfs.

    Using new boot entry, Leapp can continue the upgrade process in the initramfs after reboot
    """

    name = 'add_upgrade_boot_entry'
    consumes = (BootContent,)
    produces = ()
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        add_boot_entry()
