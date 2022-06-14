from leapp.actors import Actor
from leapp.libraries.actor.checkmountoptions import check_mount_options
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckMountOptions(Actor):
    """
    Check for mount options preventing the upgrade.

    Checks performed:
        - /var is mounted with the noexec option
    """
    name = "check_mount_options"
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        check_mount_options()
