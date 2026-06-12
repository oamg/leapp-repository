from leapp.actors import Actor
from leapp.libraries.actor import scanraid
from leapp.models import DistributionSignedRPM, RAIDInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanRaid(Actor):
    """
    Detect whether software RAID is in use on the system.

    Checks if the mdadm package is installed and whether any MD arrays
    are currently assembled and active by scanning mdadm configuration.
    """

    name = 'scan_raid'
    consumes = (DistributionSignedRPM,)
    produces = (RAIDInfo,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scanraid.process()
