from leapp.actors import Actor
from leapp.libraries.actor import scankernel
from leapp.models import InstalledTargetKernelInfo, InstalledTargetKernelVersion, KernelInfo, TransactionCompleted
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class ScanInstalledTargetKernelVersion(Actor):
    """
    Scan for the version of the newly installed kernel

    Based on the source kernel type and page size, this actor determines the
    appropriate target kernel package (e.g. kernel-core, kernel-64k-core,
    kernel-rt-core) and produces InstalledTargetKernelInfo containing the installed target kernel RPM. If the
    expected variant is missing, it falls back to the ordinary kernel for
    the same page size. Note that a fallback from a realtime to an ordinary
    kernel may occur when the target realtime kernel package is not
    available. This can happen if the user does not have a repository
    providing the realtime kernel enabled, and there is currently no way
    to verify package availability beforehand (the dnf plugin does not
    propagate this information back to the actor). In such cases, the user
    must enable the appropriate repository and install the realtime kernel
    after the upgrade manually, which is preferred to ending up with an
    unbootable system.
    """

    name = 'scan_installed_target_kernel_version'
    consumes = (TransactionCompleted, KernelInfo)
    produces = (InstalledTargetKernelInfo, InstalledTargetKernelVersion)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        scankernel.process()
