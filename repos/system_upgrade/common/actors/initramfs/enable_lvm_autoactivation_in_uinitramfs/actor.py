from leapp.actors import Actor
from leapp.libraries.actor import enable_lvm_autoactivation as enable_lvm_autoactivation_lib
from leapp.models import UpgradeInitramfsTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class EnableLVMAutoactivationInUpgradeInitramfs(Actor):
    """
    Enable LVM autoactivation in upgrade initramfs.

    Produce instructions for upgrade initramfs generation that will result in LVM
    autoactivation in the initramfs.
    """

    name = 'enable_lvm_autoactivation_in_upgrade_initramfs'
    consumes = ()
    produces = (UpgradeInitramfsTasks, )
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        enable_lvm_autoactivation_lib.emit_lvm_autoactivation_instructions()
