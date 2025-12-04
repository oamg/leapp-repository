from leapp.actors import Actor
from leapp.libraries.actor.checklvm import check_lvm
from leapp.models import DistributionSignedRPM, LVMConfig, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckLVM(Actor):
    """
    Check if the LVM is installed and ensure the target userspace container
    and initramfs are prepared to support it.

    The LVM configuration files are copied into the target userspace container
    so that the dracut is able to use them while creating the initramfs.
    The dracut LVM module is enabled by this actor as well.
    """

    name = 'check_lvm'
    consumes = (DistributionSignedRPM, LVMConfig)
    produces = (Report, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        check_lvm()
