from leapp.actors import Actor
from leapp.libraries.actor import checkselinux
from leapp.models import (
    KernelCmdline,
    KernelCmdlineArg,
    Report,
    SELinuxFacts,
    SelinuxPermissiveDecision,
    SelinuxRelabelDecision,
    TargetKernelCmdlineArgTasks
)
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSelinux(Actor):
    """
    Check SELinux status and produce decision messages for further action.

    Based on SELinux status produces decision messages to relabeling and changing status if
    necessary
    """

    name = 'check_se_linux'
    consumes = (SELinuxFacts, KernelCmdline)
    produces = (
        KernelCmdlineArg,
        Report,
        SelinuxPermissiveDecision,
        SelinuxRelabelDecision,
        TargetKernelCmdlineArgTasks,
    )
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkselinux.process()
