from leapp.actors import Actor
from leapp.libraries.actor import checkresumekernelarg
from leapp.models import KernelCmdline, TargetKernelCmdlineArgTasks, UpgradeKernelCmdlineArgTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckResumeKernelArg(Actor):
    """
    Remove the resume argument from the upgrade boot entry.

    The resume argument points to a swap device used for hibernation. During the
    upgrade the dracut resume module is excluded, so the resume device cannot be
    resolved and the system can hang during reboot. Therefore, we remove the
    resume kernel command line argument from the upgrade boot entry to prevent
    a possible hang during the upgrade reboot.

    The argument is restored on the target kernel so hibernation keeps working
    after the upgrade.
    """

    name = 'check_resume_kernel_arg'
    consumes = (KernelCmdline,)
    produces = (TargetKernelCmdlineArgTasks, UpgradeKernelCmdlineArgTasks)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkresumekernelarg.process()
