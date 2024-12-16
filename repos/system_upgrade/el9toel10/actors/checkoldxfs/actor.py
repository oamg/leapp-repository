import leapp.libraries.actor.checkoldxfs as checkoldxfs
from leapp.actors import Actor
from leapp.models import XFSInfoFacts
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckOldXFS(Actor):
    """
    Inhibit upgrade if XFS requirements for RHEL 10 are not satisfied.

    RHEL 10 introduces stricter requirements for XFS filesystems. If any XFS
    filesystem on the system lack these required features, the upgrade will be
    inhibited.

    """

    name = 'check_old_xfs'
    consumes = (XFSInfoFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        checkoldxfs.process()
