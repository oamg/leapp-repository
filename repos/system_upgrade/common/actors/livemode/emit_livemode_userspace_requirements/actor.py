from leapp.actors import Actor
from leapp.libraries.actor import emit_livemode_userspace_requirements as emit_livemode_userspace_requirements_lib
from leapp.models import LiveModeConfig, TargetUserSpaceUpgradeTasks
from leapp.tags import ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag


class EmitLiveModeRequirements(Actor):
    """
    Request addiontal packages to be installed into target userspace.

    Additional packages can be requested using LiveModeConfig.additional_packages
    """

    name = 'emit_livemode_requirements'
    consumes = (LiveModeConfig,)
    produces = (TargetUserSpaceUpgradeTasks,)
    tags = (ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag,)

    def process(self):
        emit_livemode_userspace_requirements_lib.emit_livemode_userspace_requirements()
