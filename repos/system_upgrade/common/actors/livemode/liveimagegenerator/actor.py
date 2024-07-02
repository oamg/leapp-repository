from leapp.actors import Actor
from leapp.libraries.actor.liveimagegenerator import generate_live_image
from leapp.libraries.stdlib import api
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
        livemode = next(api.consume(LiveModeConfigFacts), None)
        if not livemode or not livemode.enabled:
            return

        userspace = next(api.consume(TargetUserSpaceInfo), None)
        tasks = next(api.consume(LiveImagePreparationInfo), None)
        boot_content = next(api.consume(BootContent), None)

        kernel, initramfs, squashfs = generate_live_image(livemode, userspace, tasks, boot_content)

        api.produce(LiveModeArtifacts(
            kernel=kernel, initramfs=initramfs, squashfs=squashfs
        ))

        msg = ('\n\n'
               '============================================================\n'
               ' Live Mode artifacts have been created:\n'
               '  - {kernel}\n'
               '  - {initramfs}\n'
               '  - {squashfs}\n'
               '============================================================\n')
        msg = msg.format(kernel=kernel, initramfs=initramfs, squashfs=squashfs)
