from leapp.actors import Actor
from leapp.libraries.actor.checkpersistentmounts import check_persistent_mounts
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckPersistentMounts(Actor):
    """
    Check if mounts required to be persistent are mounted in persistent fashion.

    Checks performed:
        - if /var/lib/leapp is mounted it has an entry in /etc/fstab
    """
    name = "check_persistent_mounts"
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        check_persistent_mounts()
