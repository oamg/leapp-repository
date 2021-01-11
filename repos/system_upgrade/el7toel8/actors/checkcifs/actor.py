from leapp.actors import Actor
from leapp.libraries.actor.checkcifs import checkcifs
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckCIFS(Actor):
    """
    Check if CIFS filesystem is in use. If yes, inhibit the upgrade process.

    Actor looks for CIFS in /ets/fstab.
    If there is a CIFS entry, the upgrade is inhibited.
    """
    name = "check_cifs"
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        checkcifs(self.consume(StorageInfo))
