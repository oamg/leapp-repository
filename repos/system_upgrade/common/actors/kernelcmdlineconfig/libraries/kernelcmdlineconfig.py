from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelVersion, KernelCmdlineArg


def run_grubby_cmd(cmd):
    try:
        stdlib.run(cmd)
        if architecture.matches_architecture(architecture.ARCH_S390X):
            # On s390x we need to call zipl explicitly because of issue in grubby,
            # otherwise the entry is not updated in the ZIPL bootloader
            # See https://bugzilla.redhat.com/show_bug.cgi?id=1764306
            stdlib.run(['/usr/sbin/zipl'])

    except (OSError, stdlib.CalledProcessError) as e:
        raise StopActorExecutionError(
            "Failed to append extra arguments to kernel command line.",
            details={"details": str(e)})


def append_kernel_args_in_boot_cfg(configs_to_modify_explicitly=None):
    kernel_version = next(api.consume(InstalledTargetKernelVersion), None)
    if not kernel_version:
        return

    kernelarg_msgs = sorted(api.consume(KernelCmdlineArg), key=lambda arg: arg.key)
    if not kernelarg_msgs:
        return  # No kernel args modification was requested

    # Format the received args so they can be joined and passed to grubby --args=
    kernel_args_to_append = []
    for arg in kernelarg_msgs:
        if arg.value:
            kernel_args_to_append.append('{0}={1}'.format(arg.key, arg.value))
        else:
            kernel_args_to_append.append('{0}'.format(arg.key))

    grubby_append_args_cmd = ['grubby', '--update-kernel=/boot/vmlinuz-{}'.format(kernel_version.version),
                              '--args={}'.format(' '.join(kernel_args_to_append))]

    if configs_to_modify_explicitly:
        for config_to_modify in configs_to_modify_explicitly:
            cmd = grubby_append_args_cmd + ['-c', config_to_modify]
            run_grubby_cmd(cmd)
    else:
        run_grubby_cmd(grubby_append_args_cmd)
