from leapp.actors import Actor
from leapp.libraries.actor import checknvme
from leapp.models import (
    NVMEInfo,
    TargetUserSpacePreupgradeTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNVME(Actor):
    """
    Check if NVMe devices are used and possibly register additional actions.

    To be able to boot correctly the storage with NVMe devices, the initramfs
    needs to contain nvmf dracut module with additional possibly required data.
    Register all required actions that should happen to handle correctly systems
    with NVMe devices.

    Currently covered:
        * NVMe (PCIe)
        * NVMe-FC
    """
    # FIXME(pstodulk): update the description once the actor is fully
    # implemented

    name = 'check_nvme'
    consumes = (NVMEInfo,)
    produces = (
        Report,
        TargetUserSpacePreupgradeTasks,
        TargetUserSpaceUpgradeTasks,
        UpgradeInitramfsTasks,
        UpgradeKernelCmdlineArgTasks
    )
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checknvme.process()
