from leapp.actors import Actor
from leapp.libraries.actor import checkinstalledkernels
from leapp.models import InstalledRedHatSignedRPM, KernelInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckInstalledKernels(Actor):
    """
    Inhibit IPU (in-place upgrade) when installed kernels conflict with a safe upgrade.

    a) Inhibit when multiple kernels are installed on a s390x machine

    When on s390x architecture, we are not able to upgrade correctly
    when any kernel is expected to be uninstalled during the rpm
    upgrade transaction now. We discovered recently that removal of
    old kernels is not handled correctly during the IPU. In case the
    maximum number of kernels are installed, the oldest one is
    automatically uninstalled during the rpm upgrade transaction.

    To prevent any related troubles during the IPU, inhibit the IPU
    on s390x unless just one kernel is installed, until the issue will
    be fixed correctly.

    b) Inhibit when machine is not booted into latest installed kernel

    It is strictly required that during the upgrade the machine is
    booted into the latest installed kernel. Upgrading with older
    kernels could cause unexpected issues.
    """

    name = 'check_installed_kernels'
    consumes = (InstalledRedHatSignedRPM, KernelInfo)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkinstalledkernels.process()
