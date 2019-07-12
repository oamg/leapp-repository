from leapp.actors import Actor
from leapp.models import InstalledTargetKernelVersion, KernelCmdlineArg
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag
from leapp.libraries.actor import kernelcmdlineconfig


class KernelCmdlineConfig(Actor):
    """
    Append extra arguments to RHEL-8 kernel command line
    """

    name = 'kernelcmdlineconfig'
    consumes = (KernelCmdlineArg, InstalledTargetKernelVersion)
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        kernelcmdlineconfig.process()
