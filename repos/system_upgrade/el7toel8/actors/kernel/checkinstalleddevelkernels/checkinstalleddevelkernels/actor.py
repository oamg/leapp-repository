from leapp.actors import Actor
from leapp.libraries.actor import checkinstalleddevelkernels
from leapp.models import InstalledRedHatSignedRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckInstalledDevelKernels(Actor):
    """
    Inhibit IPU (in-place upgrade) when multiple devel kernels are installed.

    Because of an issue in DNF, the transaction can't be validated if there's
    more than one package named kernel-devel. Therefore, in this case, we
    inhibit the upgrade with a clearer remediation.
    """

    name = 'check_installed_devel_kernels'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkinstalleddevelkernels.process()
