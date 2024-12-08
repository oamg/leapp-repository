import leapp.libraries.actor.checkoldxfs as checkoldxfs
from leapp.actors import Actor
from leapp.models import XFSInfoFacts
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckOldXFS(Actor):
    """
    Check mounted XFS file systems.

    RHEL 10 requires XFS filesystems to use the v5 format (crc=1 is a good
    indicator). XFS v4 format filesystems will be incompatible with the target
    kernel and it will not be possible to mount them. If any such filesystem is
    detected, the upgrade will be inhibited.

    Also, RHEL 10 is going to address the Y2K38 problem, which requires bigger
    timestamps to support dates beyond 2038-01-19. Since RHEL 9, the "bigtime"
    feature (indicated by bigtime=1 in xfs_info) has been introduced to resolve
    this issue. If an XFS filesystem lacks this feature, a report will be
    created to just raise the awareness about the potential problem to the
    user, but the upgrade will not be blocked. This will probably be resolved
    automatically during the RHEL 10 lifetime, it is still 10+ years in future
    until this could have any real impact.

    """

    name = 'check_old_xfs'
    consumes = (XFSInfoFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        checkoldxfs.process()
