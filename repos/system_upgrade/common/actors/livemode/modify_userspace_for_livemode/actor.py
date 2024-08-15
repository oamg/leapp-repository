from leapp.actors import Actor
from leapp.libraries.actor.prepareliveimage import modify_userspace_as_configured
from leapp.libraries.stdlib import api
from leapp.models import (
    BootContent,
    LiveImagePreparationInfo,
    LiveModeConfig,
    LiveModeRequirementsTasks,
    StorageInfo,
    TargetUserSpaceInfo
)
from leapp.tags import ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag


class ModifyUserspaceForLiveMode(Actor):
    """
    Perform modifications of the userspace according to LiveModeConfig.

    Actor depends on BootContent to require that the upgrade initramfs has already
    been generated since during installation of initramfs dependencies systemd units
    might be modified, overwriting changes that might have been done by this actor.
    """

    name = 'prepare_live_image'
    consumes = (
        LiveModeConfig,
        LiveModeRequirementsTasks,
        StorageInfo,
        TargetUserSpaceInfo,
        BootContent,
    )
    produces = (LiveImagePreparationInfo,)
    tags = (ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag,)

    def process(self):
        livemode_config = next(api.consume(LiveModeConfig), None)
        userspace_info = next(api.consume(TargetUserSpaceInfo), None)
        storage = next(api.consume(StorageInfo), None)

        modify_userspace_as_configured(userspace_info, storage, livemode_config)
