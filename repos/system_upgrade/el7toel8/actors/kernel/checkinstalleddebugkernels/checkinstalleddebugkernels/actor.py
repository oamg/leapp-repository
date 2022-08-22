from leapp.actors import Actor
from leapp.libraries.actor import checkinstalleddebugkernels
from leapp.models import InstalledRedHatSignedRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckInstalledDebugKernels(Actor):
    """
    Inhibit IPU (in-place upgrade) when multiple debug kernels are installed.

    Because of an issue in DNF, the transaction can't be validated if there's
    more than one package named kernel-debug. Therefore, in this case, we
    inhibit the upgrade with a clearer remediation.
    """

    name = 'check_installed_debug_kernels'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkinstalleddebugkernels.process()
