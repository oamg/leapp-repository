from leapp.actors import Actor
from leapp.models import KernelCmdlineArg
from leapp.tags import IPUWorkflowTag, FinalizationPhaseTag
from leapp.libraries.stdlib import run, CalledProcessError
from leapp.exceptions import StopActorExecutionError


class KernelCmdlineConfig(Actor):
    """
    Append extra arguments to RHEL-8 kernel command line
    """

    name = 'kernelcmdlineconfig'
    consumes = (KernelCmdlineArg,)
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def get_rhel8_kernel_version(self):
            kernels = run(["rpm", "-q", "kernel"], split=True)["stdout"]
            for kernel in kernels:
                version = kernel.split("-", 1)[1]
                if "el8" in version:
                    return version
            raise StopActorExecutionError(
                    "Cannot get version of the installed RHEL-8 kernel",
                    details={"details": "\n".join(kernels)})

    def process(self):
        kernel_version = self.get_rhel8_kernel_version()
        for arg in self.consume(KernelCmdlineArg):
            cmd = ['grubby', '--update-kernel=/boot/vmlinuz-{}'.format(kernel_version), '--args="{}={}"'.format(arg.key, arg.value)]
            try:
                run(cmd)
            except CalledProcessError as e:
                raise StopActorExecutionError(
                       "Failed to append extra arguments to kernel command line.",
                       details={"details": str(e)})

