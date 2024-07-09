from leapp.actors import Actor
from leapp.libraries.actor.liveimagegenerator import generate_live_image_if_enabled
from leapp.models import (
    BootContent,
    LiveImagePreparationInfo,
    LiveModeArtifacts,
    LiveModeConfigFacts,
    LiveModeRequirementsTasks,
    PrepareLiveImagePostTasks,
    TargetUserSpaceInfo
)
from leapp.tags import ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag


class LiveImageGenerator(Actor):
    """
    Produces LiveModeArtifacts: kernel + live initramfs + squashfs image
    """

    name = 'live_image_generator'
    consumes = (BootContent,
                LiveModeConfigFacts,
                LiveModeRequirementsTasks,
                LiveImagePreparationInfo,
                PrepareLiveImagePostTasks,
                TargetUserSpaceInfo,)
    produces = (LiveModeArtifacts,)
    tags = (ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag,)

    def process(self):
        generate_live_image_if_enabled()
