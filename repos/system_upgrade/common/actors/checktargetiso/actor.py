from leapp.actors import Actor
from leapp.libraries.actor import check_target_iso
from leapp.models import Report, StorageInfo, TargetOSInstallationImage
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckTargetISO(Actor):
    """
    Check that the provided target ISO is a valid ISO image and is located on a persistent partition.
    """

    name = 'check_target_iso'
    consumes = (StorageInfo, TargetOSInstallationImage,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check_target_iso.perform_target_iso_checks()
