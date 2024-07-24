from leapp.actors import Actor
from leapp.libraries.actor.removeupgradeefientry import remove_upgrade_efi_entry
from leapp.libraries.common.config import architecture
from leapp.libraries.common.config.version import matches_target_version
from leapp.models import ArmWorkaroundEFIBootloaderInfo
from leapp.tags import InitRamStartPhaseTag, IPUWorkflowTag


class RemoveUpgradeEFIEntry(Actor):
    """
    Remove UEFI entry for LEAPP upgrade (see AddArmBootloaderWorkaround).
    """

    name = 'remove_upgrade_efi_entry'
    consumes = (ArmWorkaroundEFIBootloaderInfo,)
    produces = ()
    tags = (IPUWorkflowTag, InitRamStartPhaseTag)

    def process(self):
        if not architecture.matches_architecture(architecture.ARCH_ARM64):
            return

        if matches_target_version('< 9.5'):
            return

        remove_upgrade_efi_entry()
