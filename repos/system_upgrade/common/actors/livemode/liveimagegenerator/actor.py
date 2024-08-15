from leapp.actors import Actor
from leapp.libraries.actor.liveimagegenerator import generate_live_image_if_enabled
from leapp.models import (
    LiveImagePreparationInfo,
    LiveModeArtifacts,
    LiveModeConfig,
    LiveModeRequirementsTasks,
    PrepareLiveImagePostTasks,
    TargetUserSpaceInfo
)
from leapp.tags import ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag


class LiveImageGenerator(Actor):
    """
    Generates the squashfs image for the livemode upgrade
    """

    name = 'live_image_generator'
    consumes = (LiveModeConfig,
                LiveModeRequirementsTasks,
                LiveImagePreparationInfo,
                PrepareLiveImagePostTasks,
                TargetUserSpaceInfo,)
    produces = (LiveModeArtifacts,)
    tags = (ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag,)

    def process(self):
        generate_live_image_if_enabled()
