from leapp.actors import Actor
from leapp.libraries.actor.prepareliveimage import prepare_live_image
from leapp.libraries.stdlib import api
from leapp.models import (
    BootContent,
    LiveModeConfigFacts,
    LiveModeRequirementsTasks,
    PrepareLiveImageTasks,
    StorageInfo,
    TargetUserSpaceInfo,
)
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class PrepareLiveImage(Actor):
    """
    Generate the live upgrade initramfs.
    """

    name = 'prepare_live_image'
    consumes = (BootContent,
                LiveModeConfigFacts,
                LiveModeRequirementsTasks,
                StorageInfo,
                TargetUserSpaceInfo)
    produces = (PrepareLiveImageTasks,)
    tags = (InterimPreparationPhaseTag, IPUWorkflowTag,)

    def process(self):
        livemode = next(api.consume(LiveModeConfigFacts), None)
        if not livemode or not livemode.enabled:
            return

        userspace = next(api.consume(TargetUserSpaceInfo), None)
        storage = next(api.consume(StorageInfo), None)
        boot_content = next(api.consume(BootContent), None)

        api.produce(
            prepare_live_image(userspace, storage, boot_content, livemode)
        )
