from leapp.actors import Actor
from leapp.libraries.actor.scanhybridimage import scan_hybrid_image
from leapp.models import FirmwareFacts, HybridImageAzure, InstalledRPM
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanHybridImageAzure(Actor):
    """
    Check if the system is using Azure hybrid image.
    """

    name = 'scan_hybrid_image_azure'
    consumes = (InstalledRPM, FirmwareFacts)
    produces = (HybridImageAzure, Report)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scan_hybrid_image()
