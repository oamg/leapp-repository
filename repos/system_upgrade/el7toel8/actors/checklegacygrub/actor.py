from leapp.actors import Actor
from leapp.libraries.actor import check_legacy_grub as check_legacy_grub_lib
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class CheckLegacyGrub(Actor):
    """
    Check whether GRUB Legacy is installed in the MBR.

    GRUB Legacy is deprecated since RHEL 7 in favour of GRUB2.
    """

    name = 'check_grub_legacy'
    consumes = ()
    produces = (Report,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        check_legacy_grub_lib.check_grub_disks_for_legacy_grub()
