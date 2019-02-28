from leapp.actors import Actor
from leapp.libraries.actor.library import add_boot_entry, fix_grub_config_error
from leapp.models import BootContent, GrubConfigError
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class AddUpgradeBootEntry(Actor):
    """
    Add new boot entry for Leapp provided initramfs.

    Using new boot entry, Leapp can continue the upgrade process in the initramfs after reboot
    """

    name = 'add_upgrade_boot_entry'
    consumes = (BootContent, GrubConfigError)
    produces = ()
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        grub_config_error_detected = next(self.consume(GrubConfigError), GrubConfigError()).error_detected
        if grub_config_error_detected:
            fix_grub_config_error('/etc/default/grub')

        add_boot_entry()
