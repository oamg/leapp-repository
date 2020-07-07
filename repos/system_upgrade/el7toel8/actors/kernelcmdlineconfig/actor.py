import os

from leapp.actors import Actor
from leapp.models import InstalledTargetKernelVersion, KernelCmdlineArg, FirmwareFacts
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import kernelcmdlineconfig


class KernelCmdlineConfig(Actor):
    """
    Append extra arguments to RHEL-8 kernel command line
    """

    name = 'kernelcmdlineconfig'
    consumes = (KernelCmdlineArg, InstalledTargetKernelVersion, FirmwareFacts)
    produces = ()
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
        kernelcmdlineconfig.process(configs)
