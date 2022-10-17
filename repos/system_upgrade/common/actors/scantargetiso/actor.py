from leapp.actors import Actor
from leapp.libraries.actor import scan_target_os_iso
from leapp.models import CustomTargetRepository, TargetOSInstallationImage
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanTargetISO(Actor):
    """Scans the provided target OS ISO image to use as a content source for the IPU, if any."""

    name = 'scan_target_os_image'
    consumes = ()
    produces = (CustomTargetRepository, TargetOSInstallationImage,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scan_target_os_iso.inform_ipu_about_request_to_use_target_iso()
