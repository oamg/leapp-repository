from leapp.actors import Actor
from leapp.libraries.actor.checkluks import check_invalid_luks_devices
from leapp.models import CephInfo, LuksDumps, StorageInfo, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckLuks(Actor):
    """
    Check if any encrypted partitions are in use and whether they are supported for the upgrade.

    For EL8+ it's ok if the discovered used encrypted storage has LUKS2 format
    and it's bound to clevis-tpm2 token (so it can be automatically unlocked
    during the process).
    """

    name = 'check_luks'
    consumes = (CephInfo, LuksDumps, StorageInfo)
    produces = (Report, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        check_invalid_luks_devices()
