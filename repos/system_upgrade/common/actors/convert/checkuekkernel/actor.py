from leapp.actors import Actor
from leapp.libraries.actor import checkuekkernel
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckUEKKernel(Actor):
    """
    Inhibit the upgrade when the system is booted into the Unbreakable Enterprise Kernel (UEK).

    The system must be booted into the Red Hat Compatible Kernel before proceeding.
    """

    name = 'check_uek_kernel'
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkuekkernel.process()
