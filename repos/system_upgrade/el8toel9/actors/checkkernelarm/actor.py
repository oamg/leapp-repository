from leapp.actors import Actor
from leapp.libraries.actor import checkkernelarm
from leapp.models import KernelInfo, RpmTransactionTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckKernelARM(Actor):
    """
    Instruct the installation of 64k kernel on ARM machines.

    On RHEL 8 all ARM machines use kernel with the 64k pagesize.
    However, in case of RHEL 9 the default ARM kernel has 4k pagesize instead.
    Ensure that 64k kernel is installed on the target system for ARM.
    """

    name = 'check_kernel_arm'
    consumes = (KernelInfo,)
    produces = (RpmTransactionTasks,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkkernelarm.process()
