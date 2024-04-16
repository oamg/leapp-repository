from leapp.actors import Actor
from leapp.libraries.actor.inhibitwhenluks import check_invalid_luks_devices
from leapp.models import CephInfo, LuksDumps, TargetUserSpaceUpgradeTasks
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class InhibitWhenLuks(Actor):
    """
    Check if any encrypted partitions is in use. If yes, inhibit the upgrade process.

    Upgrading system with encrypted partition is not supported.
    """

    name = 'check_luks_and_inhibit'
    consumes = (LuksDumps, CephInfo)
    produces = (Report, TargetUserSpaceUpgradeTasks)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        check_invalid_luks_devices()
