from leapp.actors import Actor
from leapp.libraries.actor import check_default_initramfs as check_default_initramfs_lib
from leapp.models import DefaultInitramfsInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckDefaultInitramfs(Actor):
    """
    Checks whether the default initramfs uses problematic dracut modules.

    Checks whether dracut modules that are missing on the target system are used.
    If yes, the upgrade is inhibited.
    """

    name = 'check_default_initramfs'
    consumes = (DefaultInitramfsInfo,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check_default_initramfs_lib.check_default_initramfs()
