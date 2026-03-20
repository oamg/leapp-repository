from leapp.actors import Actor
from leapp.libraries.actor import persistentnetnamesdisable
from leapp.models import (
    PersistentNetNamesFacts,
    TargetKernelCmdlineArgTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class PersistentNetNamesDisable(Actor):
    """
    Disable systemd-udevd persistent network naming on machine with single eth0 NIC
    """

    name = 'persistentnetnamesdisable'
    consumes = (PersistentNetNamesFacts,)
    produces = (Report, TargetKernelCmdlineArgTasks, UpgradeKernelCmdlineArgTasks)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        persistentnetnamesdisable.process()
