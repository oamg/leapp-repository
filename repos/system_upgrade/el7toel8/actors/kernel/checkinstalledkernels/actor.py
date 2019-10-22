from leapp.actors import Actor
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag
from leapp.reporting import Report
from leapp.libraries.actor import library


class CheckInstalledKernels(Actor):
    """
    Inhibit IPU (in-place upgrade) when multiple kernels are installed.

    We are not able to upgrade correctly when any kernel is expected to be
    uninstalled during the rpm upgrade transaction now. This is especially
    problematic on s390x architecture.

    We discovered recently that removal of old kernels is not handled
    correctly during the IPU. In case the maximum number of kernels
    are installed, the oldest one is automatically uninstalled during
    the rpm upgrade transaction.

    To prevent any related troubles during the IPU, inhibit the IPU
    on s390x unless just one kernel is installed, until the issue will
    be fixed correctly.
    """

    name = 'check_installed_kernels'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        library.process()
