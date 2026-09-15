from leapp.actors import Actor
from leapp.libraries.actor import checkstratis
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckStratis(Actor):
    """
    Check if Stratis (stratisd) filesystems are configured in /etc/fstab.

    Stratis is supported by RHEL, but it is not handled by the leapp in-place
    upgrade. The upgrade initramfs does not contain stratisd, so such
    filesystems cannot be activated and mounted during the upgrade. If any
    Stratis entry is present in /etc/fstab, the upgrade is inhibited.
    """

    name = 'check_stratis'
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        checkstratis.process()
