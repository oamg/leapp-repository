from leapp.actors import Actor
from leapp.libraries.actor import checkstratis
from leapp.models import LiveModeConfig, StorageInfo, TargetUserSpaceUpgradeTasks
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckStratis(Actor):
    """
    Check if Stratis (stratisd) filesystems are configured in /etc/fstab.

    Stratis is supported by RHEL, but it is not handled by the leapp in-place
    upgrade. The upgrade initramfs does not contain stratisd, so such
    filesystems cannot be activated and mounted during the upgrade. If any
    Stratis entry is present in /etc/fstab, the upgrade is inhibited.

    The exception is the live mode upgrade with networking enabled. There, the
    upgrade runs from a full userspace (not the limited upgrade initramfs), so
    stratisd can be made available by installing it into the target userspace.
    In that case the upgrade is not inhibited and the required packages are
    requested to be installed into the target userspace instead.
    """

    name = 'check_stratis'
    consumes = (LiveModeConfig, StorageInfo,)
    produces = (Report, TargetUserSpaceUpgradeTasks,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        checkstratis.process()
