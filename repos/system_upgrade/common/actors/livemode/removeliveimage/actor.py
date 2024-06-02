import os

from leapp.actors import Actor
from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfigFacts, LiveModeArtifacts
from leapp.tags import ExperimentalTag, FirstBootPhaseTag, IPUWorkflowTag


class RemoveLiveImage(Actor):
    """
    Remove live mode artifacts
    """

    name = 'remove_live_image'
    consumes = (LiveModeConfigFacts, LiveModeArtifacts,)
    produces = ()
    tags = (ExperimentalTag, FirstBootPhaseTag, IPUWorkflowTag)

    def process(self):
        livemode = next(api.consume(LiveModeConfigFacts), None)
        if not livemode or not livemode.enabled:
            return

        artifacts = next(api.consume(LiveModeArtifacts), None)
        try:
            os.unlink(artifacts.squashfs)
        except (FileNotFoundError, PermissionError):
            api.current_logger().warning('Cannot remove %s' %artifacts.squashfs)

        # upgrade vmlinuz/initramfs have already been removed by another actor
        # proceed anyway
        try:
            os.unlink(artifacts.kernel)
            os.unlink(artifacts.initramfs)
        except (FileNotFoundError, PermissionError):
            pass
