from leapp.actors import Actor
from leapp.libraries.actor import checkraid
from leapp.models import RaidInfo, TargetUserSpaceUpgradeTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckRaid(Actor):
    """
    Ensure RAID configuration files are available in the target userspace.

    If mdadm software RAID is in use, copies present mdadm configuration
    files and directories into the target userspace container so that
    dracut can include them in the upgrade initramfs.
    """

    name = 'check_raid'
    consumes = (RaidInfo,)
    produces = (TargetUserSpaceUpgradeTasks,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkraid.process()
