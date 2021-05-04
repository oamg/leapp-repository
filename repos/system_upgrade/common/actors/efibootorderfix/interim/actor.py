from leapp.actors import Actor
from leapp.libraries.common import efi_reboot_fix
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class EfiInterimFix(Actor):
    """
    Adjust EFI boot entry for first reboot
    """

    name = 'efi_interim_fix'
    consumes = ()
    produces = ()
    tags = (InterimPreparationPhaseTag, IPUWorkflowTag)

    def process(self):
        efi_reboot_fix.maybe_emit_updated_boot_entry()
