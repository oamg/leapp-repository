from leapp.actors import Actor
from leapp.libraries.actor.xfsinfoscanner import scan_xfs
from leapp.models import StorageInfo, XFSInfoFacts, XFSPresence
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class XFSInfoScanner(Actor):
    """
    This actor scans all mounted mountpoints for XFS information.

    The actor checks the `StorageInfo` message, which contains details about
    the system's storage. For each mountpoint reported, it determines whether
    the filesystem is XFS and collects information about its configuration.
    Specifically, it identifies whether the XFS filesystem is using `ftype=0`,
    which requires special handling for overlay filesystems.

    The actor produces two types of messages:

    - `XFSPresence`: Indicates whether any XFS use `ftype=0`, and lists the
      mountpoints where `ftype=0` is used.

    - `XFSInfoFacts`: Contains detailed metadata about all XFS mountpoints.
      This includes sections parsed from the `xfs_info` command.

    """

    name = 'xfs_info_scanner'
    consumes = (StorageInfo,)
    produces = (XFSPresence, XFSInfoFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag,)

    def process(self):
        scan_xfs()
