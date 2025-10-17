from leapp.actors import Actor
from leapp.libraries.actor import enable_lvm_autoactivation as enable_lvm_autoactivation_lib
from leapp.models import DistributionSignedRPM, LiveModeConfig, UpgradeInitramfsTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class EnableLVMAutoactivation(Actor):
    """
    Enable LVM autoactivation in upgrade initramfs.

    Produce instructions for upgrade initramfs generation that will result in LVM
    autoactivation in the initramfs. Note that these instructions are not produced
    when the livemode is enabled.
    """

    name = 'enable_lvm_autoactivation'
    consumes = (
        DistributionSignedRPM,
        LiveModeConfig,
    )
    produces = (UpgradeInitramfsTasks, )
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        enable_lvm_autoactivation_lib.emit_lvm_autoactivation_instructions()
