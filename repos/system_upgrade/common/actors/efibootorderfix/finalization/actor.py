from leapp.actors import Actor
from leapp.libraries.common import efi_reboot_fix
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class EfiFinalizationFix(Actor):
    """
    Adjust EFI boot entry for final reboot
    """

    name = 'efi_finalization_fix'
    consumes = ()
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        efi_reboot_fix.maybe_emit_updated_boot_entry()
