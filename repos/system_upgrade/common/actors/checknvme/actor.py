from leapp.actors import Actor
from leapp.libraries.actor import checknvme
from leapp.models import (
    KernelCmdline,
    LiveModeConfig,
    NVMEInfo,
    StorageInfo,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNVME(Actor):
    """
    Check if NVMe devices are used and possibly register additional actions.

    Check whether the system uses NVMe devices. These can be connected using
    different transport technologies, e.g., PCIe, TCP, FC, etc. Transports
    handled by the current implementation:
        * PCIe (no special actions are required)
        * Fibre Channel (FC)

    When NVMe-FC devices are detected, the following actions are taken:
        * dracut, dracut-network, nvme-cli, and some others packages are installed into initramfs
        * /etc/nvme is copied into target userspace
        * the nvmf dracut module is included into upgrade initramfs
        * rd.nvmf.discover=fc,auto is added to the upgrade boot entry
        * nvme_core.multipath is added to the upgrade and target boot entry

    Conditions causing the upgrade to be inhibited:
        * detecting a NVMe device using a transport technology different than PCIe or FC
          that is used in /etc/fstab
        * missing /etc/nvme/hostnqn or /etc/nvme/hostid when NVMe-FC device is present
        * source system is RHEL 9+ and it has disabled native multipath
    """
    name = 'check_nvme'
    consumes = (LiveModeConfig, KernelCmdline, NVMEInfo, StorageInfo)
    produces = (
        Report,
        TargetKernelCmdlineArgTasks,
        TargetUserSpaceUpgradeTasks,
        UpgradeInitramfsTasks,
        UpgradeKernelCmdlineArgTasks
    )
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checknvme.process()
