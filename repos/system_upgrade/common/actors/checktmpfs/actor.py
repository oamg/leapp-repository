from leapp.actors import Actor
from leapp.libraries.actor.checktmpfs import checktmpfs
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckTmpFs(Actor):
    """
    Check if there is a /tmp entry in fstab.
    If there is, inhibit the upgrade process.

    Actor looks for /tmp in /ets/fstab.
    If there is a /tmp entry, the upgrade is inhibited.
    """

    name = "check_tmpfs"
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (
        ChecksPhaseTag,
        IPUWorkflowTag,
    )

    def process(self):
        checktmpfs(self.consume(StorageInfo))
