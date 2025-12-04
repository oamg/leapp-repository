from leapp.actors import Actor
from leapp.libraries.actor import scanlvmconfig
from leapp.models import DistributionSignedRPM, LVMConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanLVMConfig(Actor):
    """
    Scan LVM configuration.
    """

    name = 'scan_lvm_config'
    consumes = (DistributionSignedRPM,)
    produces = (LVMConfig,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scanlvmconfig.scan()
