from leapp.actors import Actor

from leapp.libraries.actor import addupgradebootloader
from leapp.libraries.common.config import architecture
from leapp.libraries.common.config.version import get_target_version
from leapp.models import TargetUserSpaceInfo, ArmWorkaroundEFIBootloaderInfo
from leapp.tags import IPUWorkflowTag, InterimPreparationPhaseTag


class AddArmBootloaderWorkaround(Actor):
    """
    Add a custom EFI entry with rhel9 bootloader to the source system and boot
    into it.
    """

    name = 'add_arm_bootloader_workaround'
    consumes = (TargetUserSpaceInfo,)
    produces = (ArmWorkaroundEFIBootloaderInfo,)
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        if not architecture.matches_architecture(architecture.ARCH_ARM64):
            return

        target_major, target_minor = tuple(map(int, get_target_version().split('.')))
        if (target_major, target_minor) < (9, 5):
            return

        addupgradebootloader.process()
