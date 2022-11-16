from leapp.actors import Actor
from leapp.libraries.actor import mount_target_iso
from leapp.models import TargetOSInstallationImage, TargetUserSpaceInfo
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class MountTargetISO(Actor):
    """Mounts target OS ISO in order to install upgrade packages from it."""

    name = 'mount_target_iso'
    consumes = (TargetUserSpaceInfo, TargetOSInstallationImage,)
    produces = ()
    tags = (PreparationPhaseTag, IPUWorkflowTag)

    def process(self):
        mount_target_iso.mount_target_iso()
