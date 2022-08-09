from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelVersion, KernelCmdlineArg, TargetKernelCmdlineArgTasks


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


def format_kernelarg_msgs_for_grubby_cmd(kernelarg_msgs):
    kernelarg_msgs = sorted(kernelarg_msgs, key=lambda arg: arg.key)
    kernel_args = []
    for arg in kernelarg_msgs:
        if arg.value:
            kernel_args.append('{0}={1}'.format(arg.key, arg.value))
        else:
            kernel_args.append('{0}'.format(arg.key))
    return ' '.join(kernel_args)


def modify_kernel_args_in_boot_cfg(configs_to_modify_explicitly=None):
    kernel_version = next(api.consume(InstalledTargetKernelVersion), None)
    if not kernel_version:
        return

    # Collect desired kernelopt modifications
    kernelargs_msgs_to_add = list(api.consume(KernelCmdlineArg))
    kernelargs_msgs_to_remove = []
    for target_kernel_arg_task in api.consume(TargetKernelCmdlineArgTasks):
        kernelargs_msgs_to_add.extend(target_kernel_arg_task.to_add)
        kernelargs_msgs_to_remove.extend(target_kernel_arg_task.to_remove)

    if not kernelargs_msgs_to_add and not kernelargs_msgs_to_remove:
        return  # There is no work to do

    grubby_modify_kernelargs_cmd = ['grubby', '--update-kernel=/boot/vmlinuz-{}'.format(kernel_version.version)]

    if kernelargs_msgs_to_add:
        grubby_modify_kernelargs_cmd += [
            '--args', '{}'.format(format_kernelarg_msgs_for_grubby_cmd(kernelargs_msgs_to_add))
        ]

    if kernelargs_msgs_to_remove:
        grubby_modify_kernelargs_cmd += [
            '--remove-args', '{}'.format(format_kernelarg_msgs_for_grubby_cmd(kernelargs_msgs_to_remove))
        ]

    if configs_to_modify_explicitly:
        for config_to_modify in configs_to_modify_explicitly:
            cmd = grubby_modify_kernelargs_cmd + ['-c', config_to_modify]
            run_grubby_cmd(cmd)
    else:
        run_grubby_cmd(grubby_modify_kernelargs_cmd)
