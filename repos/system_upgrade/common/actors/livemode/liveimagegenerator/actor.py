from leapp.actors import Actor
from leapp.libraries.actor.liveimagegenerator import generate_live_image
from leapp.libraries.stdlib import api
from leapp.models import (
    BootContent,
    LiveModeArtifacts,
    LiveModeConfigFacts,
    LiveModeRequirementsTasks,
    PrepareLiveImageTasks,
    PrepareLiveImagePostTasks,
    TargetUserSpaceInfo,
)
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class LiveImageGenerator(Actor):
    """
    Produces LiveModeArtifacts: kernel + live initramfs + squashfs image
    """

    name = 'live_image_generator'
    consumes = (BootContent,
                LiveModeConfigFacts,
                LiveModeRequirementsTasks,
                PrepareLiveImageTasks,
                PrepareLiveImagePostTasks,
                TargetUserSpaceInfo,)
    produces = (LiveModeArtifacts,)
    tags = (InterimPreparationPhaseTag, IPUWorkflowTag,)

    def process(self):
        livemode = next(api.consume(LiveModeConfigFacts), None)
        if not livemode or not livemode.enabled:
            return

        userspace = next(api.consume(TargetUserSpaceInfo), None)
        tasks = next(api.consume(PrepareLiveImageTasks), None)
        boot_content = next(api.consume(BootContent), None)

        kernel, initramfs, squashfs = generate_live_image(
            livemode, userspace, tasks, boot_content)

        api.produce(LiveModeArtifacts(
            kernel=kernel, initramfs=initramfs, squashfs=squashfs
        ))

        api.current_logger().info('\n\n'
            '============================================================\n'
            ' Live Mode artifacts have been created:\n'
            '  - %s\n'
            '  - %s\n'
            '  - %s\n'
            '============================================================\n'
            % (kernel, initramfs, squashfs)
        )
