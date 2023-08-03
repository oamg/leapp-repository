from leapp.actors import Actor
from leapp.libraries.actor import scankernel
from leapp.models import InstalledTargetKernelInfo, InstalledTargetKernelVersion, KernelInfo, TransactionCompleted
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class ScanInstalledTargetKernelVersion(Actor):
    """
    Scan for the version of the newly installed kernel

    This actor will query rpm for all kernel-core packages and reports the
    first matching target system kernel RPM. In case the RHEL Real Time has
    been detected on the original system, the kernel-rt-core rpm is searched.
    If the rpm is missing, fallback for standard kernel RPM.
    """

    name = 'scan_installed_target_kernel_version'
    consumes = (TransactionCompleted, KernelInfo)
    produces = (InstalledTargetKernelInfo, InstalledTargetKernelVersion)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        scankernel.process()
