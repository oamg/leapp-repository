from leapp.actors import Actor
from leapp.libraries.actor import scan_source_kernel as scan_source_kernel_lib
from leapp.models import DistributionSignedRPM, KernelInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanSourceKernel(Actor):
    """
    Scan the source system kernel.
    """

    name = 'scan_source_kernel'
    consumes = (DistributionSignedRPM,)
    produces = (KernelInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scan_source_kernel_lib.scan_source_kernel()
