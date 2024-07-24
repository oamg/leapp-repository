from leapp.actors import Actor
from leapp.libraries.actor import addupgradebootloader
from leapp.libraries.common.config import architecture
from leapp.libraries.common.config.version import matches_target_version
from leapp.models import ArmWorkaroundEFIBootloaderInfo, TargetUserSpaceInfo
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class AddArmBootloaderWorkaround(Actor):
    """
    Workaround for ARM Upgrades from RHEL8 to RHEL9.5 onwards

    This actor addresses an issue encountered during the upgrade process on ARM
    systems. Specifically, the problem arises due to an incompatibility between
    the GRUB bootloader used in RHEL 8 and the newer kernels from RHEL 9.5
    onwards. When the kernel of the target system is loaded using the
    bootloader from the source system, this incompatibility causes the
    bootloader to crash, halting the upgrade.

    To mitigate this issue, the following steps are implemented:

    Before the Upgrade (handled by CheckArmBootloader):

    * Install required RPM packages:
      - Specific packages, including an updated GRUB bootloader and shim for
        ARM (grub2-efi-aa64 and shim-aa64), are installed to ensure
        compatibility with the newer kernel.

    Before the Upgrade (this actor):

    * Create a new Upgrade EFI entry:
      - A new EFI boot entry is created and populated with the updated RHEL 9
        bootloader that is compatible with the new kernel.

    * Preserve the original EFI boot entry and GRUB configuration:
      - The original EFI boot entry and GRUB configuration remain unchanged to
        ensure system stability.

    After the Upgrade (handled by RemoveUpgradeEFIEntry):

    * Remove the upgrade EFI boot entry:
      - The temporary EFI boot entry created for the upgrade is removed to
        restore the system to its pre-upgrade state.

    """

    name = 'add_arm_bootloader_workaround'
    consumes = (TargetUserSpaceInfo,)
    produces = (ArmWorkaroundEFIBootloaderInfo,)
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        if not architecture.matches_architecture(architecture.ARCH_ARM64):
            return

        if matches_target_version('< 9.5'):
            return

        addupgradebootloader.process()
