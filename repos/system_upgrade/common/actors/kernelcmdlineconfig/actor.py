import os

from leapp import reporting
from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import kernelcmdlineconfig
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts, InstalledTargetKernelInfo, KernelCmdlineArg, TargetKernelCmdlineArgTasks
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class KernelCmdlineConfig(Actor):
    """
    Append extra arguments to the target RHEL kernel command line
    """

    name = 'kernelcmdlineconfig'
    consumes = (KernelCmdlineArg, InstalledTargetKernelInfo, FirmwareFacts, TargetKernelCmdlineArgTasks)
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

        try:
            kernelcmdlineconfig.modify_kernel_args_in_boot_cfg(configs)
        except kernelcmdlineconfig.ReadOfKernelArgsError as e:
            api.current_logger().error(str(e))
            reporting.create_report([
                reporting.Title('Could not retrieve kernel command line arguments: {}'.format(e)),
                reporting.Summary(
                    'Unable to retrieve the existing kernel command line arguments in order'
                    ' to set the default value for future installed kernels.  After the'
                    ' system has been rebooted into the new version of RHEL, you should'
                    ' check what kernel command line options are present in /proc/cmdline'
                    ' and copy them into /etc/kernel/cmdline before installing any new kernels.'
                ),
                reporting.Severity(reporting.Severity.MEDIUM),
                reporting.Groups([
                    reporting.Groups.BOOT,
                    reporting.Groups.KERNEL,
                    reporting.Groups.POST,
                ]),
                reporting.RelatedResource('file', '/etc/kernel/cmdline'),
                reporting.RelatedResource('file', '/proc/cmdline'),
            ])
            return
