from leapp.actors import Actor
from leapp.libraries.actor.library import check_xfs
from leapp.models import StorageInfo, XFSPresence
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckXFS(Actor):
    """
    Check if XFS filesystem is in use.

    If XFS filesystem without ftype is in use, produce a message to influence
    PrepareUpgradeTransaction actor about necessary steps during execution.
    """

    name = 'check_xfs'
    consumes = (StorageInfo,)
    produces = (XFSPresence,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        check_xfs()
