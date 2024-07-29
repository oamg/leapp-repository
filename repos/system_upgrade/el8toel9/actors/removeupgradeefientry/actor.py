from leapp.actors import Actor
from leapp.libraries.actor.removeupgradeefientry import remove_upgrade_efi_entry
from leapp.libraries.common.config import architecture
from leapp.libraries.common.config.version import get_target_version
from leapp.models import UpgradeEFIBootEntry
from leapp.tags import InitRamStartPhaseTag, IPUWorkflowTag


class RemoveUpgradeEFIEntry(Actor):
    """
    Remove UEFI entry for LEAPP upgrade.

    """

    name = 'remove_upgrade_boot_entry'
    consumes = (UpgradeEFIBootEntry,)
    produces = ()
    tags = (IPUWorkflowTag, InitRamStartPhaseTag)

    def process(self):
        if not architecture.matches_architecture(architecture.ARCH_ARM64):
            return

        target_major, target_minor = tuple(map(int, get_target_version().split('.')))
        if (target_major, target_minor) < (9, 5):
            return

        remove_upgrade_efi_entry()
