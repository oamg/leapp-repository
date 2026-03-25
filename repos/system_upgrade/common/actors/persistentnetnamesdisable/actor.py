from leapp.actors import Actor
from leapp.libraries.actor import persistentnetnamesdisable
from leapp.models import (
    KernelCmdline,
    PersistentNetNamesFacts,
    TargetKernelCmdlineArgTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class PersistentNetNamesDisable(Actor):
    """
    Check whether the system has any (physical) NICs with kernel naming (ethX)

    The kernel naming is in general unstable - there is no guarantee of persistent
    NIC names between reboots, so eth0 can becaome eth3 and vice versa. If the
    system has more than one physical network interface, the kernel naming must
    not be used otherwise the upgrade is inhibited. The report contains remediation
    hints for user to resolve the problem before the upgrade.

    On systems with only one physical network interface with eth0 NIC, register
    task to disable systemd-udevd persistent network naming (set `net.ifnames=0`
    on kernel cmdline for the upgrade environment and the upgraded system.
    """

    name = 'persistentnetnamesdisable'
    consumes = (PersistentNetNamesFacts, KernelCmdline)
    produces = (Report, TargetKernelCmdlineArgTasks, UpgradeKernelCmdlineArgTasks)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        persistentnetnamesdisable.process()
