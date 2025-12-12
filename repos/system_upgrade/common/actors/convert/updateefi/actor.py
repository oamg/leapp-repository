from leapp.actors import Actor
from leapp.libraries.actor import updateefi
from leapp.models import FirmwareFacts
from leapp.reporting import Report
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class UpdateEfiEntry(Actor):
    """
    Update EFI directory and entry during conversion.

    During conversion, removes leftover source distro EFI directory on the ESP
    (EFI System Partition) and it's EFI boot entry. It also adds a new boot
    entry for the target distro.

    This actor does nothing when not converting.
    """

    name = "update_efi"
    consumes = (FirmwareFacts,)
    produces = (Report,)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        updateefi.process()
