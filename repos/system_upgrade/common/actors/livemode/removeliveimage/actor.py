from leapp.actors import Actor
from leapp.libraries.actor import remove_live_image as remove_live_image_lib
from leapp.models import LiveModeArtifacts, LiveModeConfig
from leapp.tags import ExperimentalTag, FirstBootPhaseTag, IPUWorkflowTag


class RemoveLiveImage(Actor):
    """
    Remove live mode artifacts
    """

    name = 'remove_live_image'
    consumes = (LiveModeConfig, LiveModeArtifacts,)
    produces = ()
    tags = (ExperimentalTag, FirstBootPhaseTag, IPUWorkflowTag)

    def process(self):
        remove_live_image_lib.remove_live_image()
