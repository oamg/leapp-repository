import leapp.libraries.actor.checkarmbootloader as checkarmbootloader
from leapp.actors import Actor
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckArmBootloader(Actor):
    """
    Inhibit ARM system upgrades on path with incompatible kernel/bootloader

    Due to an incompatibility of RHEL8 bootloader with newer versions of kernel
    on RHEL9 since version 9.5, the upgrade cannot be performed as the old
    bootloader cannot load the new kernel when entering the interim phase.

    This is temporary workaround until the issue is resolved.

    """

    name = 'check_arm_bootloader'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        checkarmbootloader.process()
