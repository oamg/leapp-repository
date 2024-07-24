import leapp.libraries.actor.checkarmbootloader as checkarmbootloader
from leapp.actors import Actor
from leapp.models import TargetUserSpacePreupgradeTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckArmBootloader(Actor):
    """
    Install required RPM packages for ARM system upgrades on paths with
    incompatible kernel/bootloader.

    Due to an incompatibility of the RHEL8 bootloader with newer versions of
    the kernel on RHEL9 (from version 9.5 onward), the upgrade requires the
    installation of specific packages to support the new kernel during the
    interim phase.

    """

    name = 'check_arm_bootloader'
    consumes = ()
    produces = (TargetUserSpacePreupgradeTasks,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        checkarmbootloader.process()
