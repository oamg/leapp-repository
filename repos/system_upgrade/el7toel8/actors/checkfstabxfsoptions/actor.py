from leapp.actors import Actor
from leapp.libraries.actor import checkfstabxfsoptions
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckFstabXFSOptions(Actor):
    """
    Check the FSTAB file for the deprecated / removed XFS mount options.

    Some mount options for XFS have been deprecated on RHEL 7 and already
    removed on RHEL 8. If any such an option is present in the FSTAB,
    it's impossible to boot the RHEL 8 system without the manual update of the
    file.

    Check whether any of these options are present in the FSTAB file
    and inhibit the upgrade in such a case.
    """

    name = 'checkfstabxfsoptions'
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkfstabxfsoptions.process()
