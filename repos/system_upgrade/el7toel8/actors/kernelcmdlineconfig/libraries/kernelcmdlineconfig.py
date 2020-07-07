from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelVersion, KernelCmdlineArg


def process(configs=None):
    kernel_version = next(api.consume(InstalledTargetKernelVersion), None)
    if kernel_version:
        while True:
            config = []
            if configs:
                config = ['-c', configs.pop(0)]
            for arg in api.consume(KernelCmdlineArg):
                cmd = ['grubby', '--update-kernel=/boot/vmlinuz-{}'.format(kernel_version.version),
                       '--args={}={}'.format(arg.key, arg.value)]
                cmd += config
                try:
                    stdlib.run(cmd)
                    if architecture.matches_architecture(architecture.ARCH_S390X):
                        # on s390x we need to call zipl explicitly because of issue in grubby,
                        # otherwise the entry is not updated in the ZIPL bootloader
                        # See https://bugzilla.redhat.com/show_bug.cgi?id=1764306
                        stdlib.run(['/usr/sbin/zipl'])

                except (OSError, stdlib.CalledProcessError) as e:
                    raise StopActorExecutionError(
                        "Failed to append extra arguments to kernel command line.",
                        details={"details": str(e)})
            if not configs:
                break
