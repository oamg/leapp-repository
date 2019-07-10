from leapp.actors import Actor
from leapp.libraries.actor import scankernel
from leapp.models import InstalledTargetKernelVersion, TransactionCompleted
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class ScanInstalledTargetKernelVersion(Actor):
    """
    Scan for the version of the newly installed kernel

    This actor will query rpm for all kernel packages and reports the first matching el8 kernel RPM version.
    """

    name = 'scan_installed_target_kernel_version'
    consumes = (TransactionCompleted,)
    produces = (InstalledTargetKernelVersion,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        scankernel.process()
