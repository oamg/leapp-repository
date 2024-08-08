from leapp.actors import Actor
from leapp.libraries.actor.prepareliveimage import prepare_live_image
from leapp.libraries.stdlib import api
from leapp.models import (
    BootContent,
    LiveImagePreparationInfo,
    LiveModeConfigFacts,
    LiveModeRequirementsTasks,
    StorageInfo,
    TargetUserSpaceInfo
)
from leapp.tags import ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag


class PrepareLiveImage(Actor):
    """
    Generate the live upgrade initramfs.

    Actor depends on BootContent to require that the upgrade initramfs has already
    been generated since during installation of initramfs dependencies systemd units
    might be modified, overwriting changes that might have been done by this actor.
    """

    name = 'prepare_live_image'
    consumes = (
        LiveModeConfigFacts,
        LiveModeRequirementsTasks,
        StorageInfo,
        TargetUserSpaceInfo,
        BootContent,
    )
    produces = (LiveImagePreparationInfo,)
    tags = (ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag,)

    def process(self):
        livemode = next(api.consume(LiveModeConfigFacts), None)
        if not livemode or not livemode.enabled:
            return

        userspace = next(api.consume(TargetUserSpaceInfo), None)
        storage = next(api.consume(StorageInfo), None)
        boot_content = next(api.consume(BootContent), None)

        prepare_live_image(userspace, storage, boot_content, livemode)
