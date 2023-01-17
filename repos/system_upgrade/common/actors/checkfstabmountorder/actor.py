from leapp.actors import Actor
from leapp.libraries.actor.checkfstabmountorder import check_fstab_mount_order
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckFstabMountOrder(Actor):
    """
    Checks order of entries in /etc/fstab based on their mount point and inhibits upgrade if overshadowing is detected.
    """

    name = "check_fstab_mount_order"
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        check_fstab_mount_order()
