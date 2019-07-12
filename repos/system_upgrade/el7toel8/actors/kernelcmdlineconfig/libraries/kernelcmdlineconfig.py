from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelVersion, KernelCmdlineArg


def process():
    kernel_version = next(api.consume(InstalledTargetKernelVersion), None)
    if kernel_version:
        for arg in api.consume(KernelCmdlineArg):
            cmd = ['grubby', '--update-kernel=/boot/vmlinuz-{}'.format(kernel_version.version),
                   '--args={}={}'.format(arg.key, arg.value)]
            try:
                stdlib.run(cmd)
            except (OSError, stdlib.CalledProcessError) as e:
                raise StopActorExecutionError(
                    "Failed to append extra arguments to kernel command line.",
                    details={"details": str(e)})
