import os

from leapp.actors import Actor
from leapp.libraries.common.fstab import FSTAB_LOGFILE
from leapp.models import ModifiedFstabContents
from leapp.tags import IPUWorkflowTag, FinalizationPhaseTag


class RemoveInvalidFstabOptions(Actor):
    """
    Remove options for XFS mounts that are invalid on RHEL 8.
    """

    name = 'remove_invalid_fstab_options'
    consumes = (ModifiedFstabContents,)
    produces = ()
    tags = (IPUWorkflowTag, FinalizationPhaseTag)

    def process(self):
        fstab_contents = next(self.consume(ModifiedFstabContents), None)
        if not fstab_contents:
            return

        with open('/etc/fstab', 'w') as fstab:
            fstab.writelines(fstab_contents.lines)
        # clean up
        if os.path.exists(FSTAB_LOGFILE):
            os.remove(FSTAB_LOGFILE)
