import os

from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.addupgradebootentry import add_boot_entry, fix_grub_config_error
from leapp.models import BootContent, FirmwareFacts, GrubConfigError, TargetKernelCmdlineArgTasks, TransactionDryRun
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class AddUpgradeBootEntry(Actor):
    """
    Add new boot entry for Leapp provided initramfs.

    Using new boot entry, Leapp can continue the upgrade process in the initramfs after reboot
    """

    name = 'add_upgrade_boot_entry'
    consumes = (BootContent, GrubConfigError, FirmwareFacts, TransactionDryRun)
    produces = (TargetKernelCmdlineArgTasks,)
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        for grub_config_error in self.consume(GrubConfigError):
            if grub_config_error.error_detected:
                fix_grub_config_error('/etc/default/grub', grub_config_error.error_type)

        configs = None
        ff = next(self.consume(FirmwareFacts), None)
        if not ff:
            raise StopActorExecutionError(
                'Could not identify system firmware',
                details={'details': 'Actor did not receive FirmwareFacts message.'}
            )

        # related to issue with hybrid BIOS and UEFI images
        # https://bugzilla.redhat.com/show_bug.cgi?id=1667028
        if ff.firmware == 'bios' and os.path.ismount('/boot/efi') and os.path.isfile('/boot/efi/EFI/redhat/grub.cfg'):
            configs = ['/boot/grub2/grub.cfg', '/boot/efi/EFI/redhat/grub.cfg']
        add_boot_entry(configs)
