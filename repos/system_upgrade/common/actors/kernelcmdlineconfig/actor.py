import os

from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import kernelcmdlineconfig
from leapp.models import FirmwareFacts, InstalledTargetKernelInfo, KernelCmdlineArg, TargetKernelCmdlineArgTasks
from leapp.reporting import Report
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class KernelCmdlineConfig(Actor):
    """
    Append extra arguments to the target RHEL kernel command line
    """

    name = 'kernelcmdlineconfig'
    consumes = (KernelCmdlineArg, InstalledTargetKernelInfo, FirmwareFacts, TargetKernelCmdlineArgTasks)
    produces = (Report,)
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):

        configs = None
        ff = next(self.consume(FirmwareFacts), None)
        if not ff:
            raise StopActorExecutionError(
                'Could not identify system firmware',
                details={'details': 'Actor did not receive FirmwareFacts message.'}
            )

        if ff.firmware == 'bios' and os.path.ismount('/boot/efi'):
            configs = ['/boot/grub2/grub.cfg', '/boot/efi/EFI/redhat/grub.cfg']

        kernelcmdlineconfig.entrypoint(configs)
