import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.common.config import architecture, version
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelInfo, KernelCmdlineArg, TargetKernelCmdlineArgTasks

KERNEL_CMDLINE_FILE = "/etc/kernel/cmdline"


class ReadOfKernelArgsError(Exception):
    """
    Failed to retrieve the kernel command line arguments
    """


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


def set_default_kernel_args(kernel_args):
    if (architecture.matches_architecture(architecture.ARCH_S390X) or
            version.matches_target_version(">= 9.0")):
        # Put kernel_args into /etc/kernel/cmdline
        with open(KERNEL_CMDLINE_FILE, 'w') as f:
            f.write(kernel_args)
    else:
        # Use grub2-editenv to put the kernel args into /boot/grub2/grubenv
        stdlib.run(['grub2-editenv', '-', 'set', 'kernelopts={}'.format(kernel_args)])


def modify_kernel_args_in_boot_cfg(configs_to_modify_explicitly=None):
    kernel_info = next(api.consume(InstalledTargetKernelInfo), None)
    if not kernel_info:
        return

    # Collect desired kernelopt modifications

    kernelargs_msgs_to_add = list(api.consume(KernelCmdlineArg))
    kernelargs_msgs_to_remove = []
    for target_kernel_arg_task in api.consume(TargetKernelCmdlineArgTasks):
        kernelargs_msgs_to_add.extend(target_kernel_arg_task.to_add)
        kernelargs_msgs_to_remove.extend(target_kernel_arg_task.to_remove)

    if not kernelargs_msgs_to_add and not kernelargs_msgs_to_remove:
        return  # There is no work to do

    # Modify the kernel cmdline for the default kernel

    grubby_modify_kernelargs_cmd = ['grubby', '--update-kernel={0}'.format(kernel_info.kernel_img_path)]

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

    # Copy the args for the default kernel to be for all kernels.

    kernel_args = None
    cmd = ['grubby', '--info', kernel_info.kernel_img_path]
    output = stdlib.run(cmd, split=False)
    for record in output['stdout'].splitlines():
        # This could be done with one regex but it's cleaner to parse it as
        # structured data.
        if record.startswith('args='):
            data = record.split("=", 1)[1]
            matches = re.match(r'^([\'"]?)(.*)\1$', data)
            kernel_args = matches.group(2)
            break
    else:
        raise ReadOfKernelArgsError(
            "Failed to retrieve kernel command line to save for future installed kernels."
        )

    set_default_kernel_args(kernel_args)
