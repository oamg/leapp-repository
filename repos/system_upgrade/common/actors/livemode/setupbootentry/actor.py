from leapp.actors import Actor
from leapp.libraries.actor.setupbootentry import prepare_live_cmdline, setup_boot_entry
from leapp.libraries.stdlib import api
from leapp.models import (
    BootContent,
    LiveBootEntryTasks,
    LiveModeArtifacts,
    LiveModeConfigFacts,
    LiveModeRequirementsTasks,
    PrepareLiveImageTasks,
    PrepareLiveImagePostTasks,
    TargetUserSpaceInfo,
    TargetKernelCmdlineArgTasks,
)
from leapp.tags import ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag


class SetupBootEntry(Actor):
    """
    Setup the live boot entry with grubby.
    """

    name = 'setup_boot_entry'
    consumes = (BootContent,
                LiveModeArtifacts,
                LiveModeConfigFacts,
                TargetUserSpaceInfo,
                TargetKernelCmdlineArgTasks)
    produces = (LiveBootEntryTasks,)
    tags = (ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag,)

    def process(self):
        livemode = next(api.consume(LiveModeConfigFacts), None)
        if not livemode or not livemode.enabled:
            return

        userspace = next(api.consume(TargetUserSpaceInfo), None)
        boot_content = next(api.consume(BootContent), None)
        artifacts = next(api.consume(LiveModeArtifacts), None)

        root, args = prepare_live_cmdline(artifacts.squashfs, livemode)
        grubby = setup_boot_entry(root, args, boot_content)
        api.produce(LiveBootEntryTasks(grubby=grubby))
