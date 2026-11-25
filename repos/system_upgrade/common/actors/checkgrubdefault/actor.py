from leapp.actors import Actor
from leapp.libraries.actor import checkgrubdefault
from leapp.models import DefaultGrubInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckGrubDefault(Actor):
    """
    Check whether GRUB is configured to boot the saved default boot entry.

    GRUB uses the default boot entry saved in the GRUB environment block (the
    one set e.g. by grubby) only when GRUB_DEFAULT is set to "saved" in the
    /etc/default/grub file. With any other value (e.g. GRUB_DEFAULT=0) the
    saved entry is ignored, including the one Leapp sets for the kernel of the
    target system.

    Report the situation, so the user can review the configuration and
    correctly set the default boot entry after the upgrade.
    """

    name = 'check_grub_default'
    consumes = (DefaultGrubInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkgrubdefault.process()
