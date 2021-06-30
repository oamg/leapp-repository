from leapp.actors import Actor
from leapp.libraries.actor.xfsinfoscanner import scan_xfs
from leapp.models import StorageInfo, XFSPresence
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class XFSInfoScanner(Actor):
    """
    This actor scans all mounted mountpoints for XFS information

    The actor will check each mountpoint reported in the StorageInfo message, if the mountpoint is a partition with XFS
    using ftype = 0. The actor will produce a message with the findings.
    It will contain a list of all XFS mountpoints with ftype = 0 so that those mountpoints can be handled appropriately
    for the overlayfs that is going to be created.
    """

    name = 'xfs_info_scanner'
    consumes = (StorageInfo,)
    produces = (XFSPresence,)
    tags = (FactsPhaseTag, IPUWorkflowTag,)

    def process(self):
        scan_xfs()
