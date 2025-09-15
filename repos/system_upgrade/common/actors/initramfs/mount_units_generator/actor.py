from leapp.actors import Actor
from leapp.libraries.actor import mount_unit_generator as mount_unit_generator_lib
from leapp.models import TargetUserSpaceInfo, UpgradeInitramfsTasks
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class MountUnitGenerator(Actor):
    """
    Sets up storage initialization using systemd's mount units in the upgrade container.
    """

    name = 'mount_unit_generator'
    consumes = (
        TargetUserSpaceInfo,
    )
    produces = (
        UpgradeInitramfsTasks,
    )
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        mount_unit_generator_lib.setup_storage_initialization()
