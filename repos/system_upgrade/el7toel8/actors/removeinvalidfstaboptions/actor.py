import os

from leapp.actors import Actor
from leapp.libraries.common.fstab import drop_xfs_options
from leapp.models import FstabSignal
from leapp.tags import IPUWorkflowTag, FinalizationPhaseTag


class RemoveInvalidFstabOptions(Actor):
    """
    Remove options for XFS mounts that are invalid on RHEL 8.
    """

    name = 'remove_invalid_fstab_options'
    consumes = (FstabSignal,)
    produces = ()
    tags = (IPUWorkflowTag, FinalizationPhaseTag)

    def process(self):
        if not next(self.consume(FstabSignal), None):
            return

        with open('/etc/fstab', 'r') as fstab:
            lines = fstab.readlines()
        with open('/etc/fstab', 'w') as fstab:
            fstab.writelines(drop_xfs_options(lines))
        # clean up
        if os.path.exists('/var/log/etc/fstab.new'):
            os.remove('/var/log/etc/fstab.new')
