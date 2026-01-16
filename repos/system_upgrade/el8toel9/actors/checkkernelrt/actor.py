from leapp.actors import Actor
from leapp.libraries.actor import checkkernelrt
from leapp.models import DistributionSignedRPM, RpmTransactionTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckKernelRT(Actor):
    """
    Workaround kernel-rt upgrade candidate issue during RHEL 8 to RHEL 9 upgrade.

    Removes the kernel-rt metapackage to avoid RPM transaction failures and ensures
    kernel-rt-core is explicitly upgraded so real-time kernels continue to work.
    """

    name = 'check_kernel_rt'
    consumes = (DistributionSignedRPM,)
    produces = (RpmTransactionTasks,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkkernelrt.process()
