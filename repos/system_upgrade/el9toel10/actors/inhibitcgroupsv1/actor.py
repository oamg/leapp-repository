from leapp.actors import Actor
from leapp.libraries.actor import inhibitcgroupsv1
from leapp.models import KernelCmdline
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class InhibitCgroupsv1(Actor):
    """
    Inhibit upgrade if cgroups-v1 are enabled

    Support for cgroups-v1 was deprecated in RHEL 9 and removed in RHEL 10.
    Both legacy and hybrid modes are unsupported, only the unified cgroup
    hierarchy (cgroups-v2) is supported.
    """

    name = 'inhibit_cgroupsv1'
    consumes = (KernelCmdline,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        inhibitcgroupsv1.process()
