import re

from leapp import reporting
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


def use_cmdline_file():
    if (architecture.matches_architecture(architecture.ARCH_S390X) or
            version.matches_target_version('>= 9.0')):
        return True
    return False


def run_grubby_cmd(cmd):
    try:
        stdlib.run(cmd)
        if architecture.matches_architecture(architecture.ARCH_S390X):
            # On s390x we need to call zipl explicitly because of issue in grubby,
            # otherwise the entry is not updated in the ZIPL bootloader
            # See https://bugzilla.redhat.com/show_bug.cgi?id=1764306
            stdlib.run(['/usr/sbin/zipl'])

    except (OSError, stdlib.CalledProcessError) as e:
        # In most cases we don't raise StopActorExecutionError in post-upgrade
        # actors.
        #
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
    if use_cmdline_file():
        # Put kernel_args into /etc/kernel/cmdline
        with open(KERNEL_CMDLINE_FILE, 'w') as f:
            f.write(kernel_args)
            # new line is expected in the EOF (POSIX).
            f.write('\n')
    else:
        # Use grub2-editenv to put the kernel args into /boot/grub2/grubenv
        stdlib.run(['grub2-editenv', '-', 'set', 'kernelopts={}'.format(kernel_args)])


def retrieve_arguments_to_modify():
    """
    Retrieve the arguments other actors would like to add or remove from the kernel cmdline.
    """
    kernelargs_msgs_to_add = list(api.consume(KernelCmdlineArg))
    kernelargs_msgs_to_remove = []

    for target_kernel_arg_task in api.consume(TargetKernelCmdlineArgTasks):
        kernelargs_msgs_to_add.extend(target_kernel_arg_task.to_add)
        kernelargs_msgs_to_remove.extend(target_kernel_arg_task.to_remove)

    return kernelargs_msgs_to_add, kernelargs_msgs_to_remove


def modify_args_for_default_kernel(kernel_info,
                                   kernelargs_msgs_to_add,
                                   kernelargs_msgs_to_remove,
                                   configs_to_modify_explicitly=None):
    grubby_modify_kernelargs_cmd = ['grubby',
                                    '--update-kernel={0}'.format(kernel_info.kernel_img_path)]

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


def _extract_grubby_value(record):
    data = record.split('=', 1)[1]
    matches = re.match(r'^([\'"]?)(.*)\1$', data)
    return matches.group(2)


def retrieve_args_for_default_kernel(kernel_info):
    # Copy the args for the default kernel to all kernels.
    kernel_args = None
    kernel_root = None
    cmd = ['grubby', '--info', kernel_info.kernel_img_path]
    output = stdlib.run(cmd, split=False)
    for record in output['stdout'].splitlines():
        # This could be done with one regex but it's cleaner to parse it as
        # structured data.
        if record.startswith('args='):
            temp_kernel_args = _extract_grubby_value(record)

            if kernel_args:
                api.current_logger().warning('Grubby output is malformed:'
                                             ' `args=` is listed more than once.')
                if kernel_args != temp_kernel_args:
                    raise ReadOfKernelArgsError('Grubby listed `args=` multiple'
                                                ' times with different values.')
            kernel_args = _extract_grubby_value(record)
        elif record.startswith('root='):
            api.current_logger().warning('Grubby output is malformed:'
                                         ' `root=` is listed more than once.')
            if kernel_root:
                raise ReadOfKernelArgsError('Grubby listed `root=` multiple'
                                            ' times with different values')
            kernel_root = _extract_grubby_value(record)

    if not kernel_args or not kernel_root:
        raise ReadOfKernelArgsError(
            'Failed to retrieve kernel command line to save for future installed'
            ' kernels: root={}, args={}'.format(kernel_root, kernel_args)
        )

    return kernel_root, kernel_args


def modify_kernel_args_in_boot_cfg(configs_to_modify_explicitly=None):
    kernel_info = next(api.consume(InstalledTargetKernelInfo), None)
    if not kernel_info:
        return

    # Collect desired kernelopt modifications
    kernelargs_msgs_to_add, kernelargs_msgs_to_remove = retrieve_arguments_to_modify()
    if not kernelargs_msgs_to_add and not kernelargs_msgs_to_remove:
        # Nothing to do
        return

    # Modify the kernel cmdline for the default kernel
    modify_args_for_default_kernel(kernel_info,
                                   kernelargs_msgs_to_add,
                                   kernelargs_msgs_to_remove,
                                   configs_to_modify_explicitly)

    # Copy kernel params from the default kernel to all the kernels
    kernel_root, kernel_args = retrieve_args_for_default_kernel(kernel_info)
    complete_kernel_args = 'root={} {}'.format(kernel_root, kernel_args)
    set_default_kernel_args(complete_kernel_args)


def entrypoint(configs=None):
    try:
        modify_kernel_args_in_boot_cfg(configs)
    except ReadOfKernelArgsError as e:
        api.current_logger().error(str(e))

        if use_cmdline_file():
            report_hint = reporting.Hints(
                'After the system has been rebooted into the new version of RHEL, you'
                ' should take the kernel cmdline arguments from /proc/cmdline (Everything'
                ' except the BOOT_IMAGE entry and initrd entries) and copy them into'
                ' /etc/kernel/cmdline before installing any new kernels.'
            )
        else:
            report_hint = reporting.Hints(
                'After the system has been rebooted into the new version of RHEL, you'
                ' should take the kernel cmdline arguments from /proc/cmdline (Everything'
                ' except the BOOT_IMAGE entry and initrd entries) and then use the'
                ' grub2-editenv command to make them the default kernel args.  For example,'
                ' if /proc/cmdline contains:\n\n'
                '    BOOT_IMAGE=(hd0,msdos1)/vmlinuz-4.18.0-425.3.1.el8.x86_64'
                ' root=/dev/mapper/rhel_ibm--root ro console=tty0'
                ' console=ttyS0,115200 rd_NO_PLYMOUTH\n\n'
                ' then run the following grub2-editenv command:\n\n'
                '    # grub2-editenv - set "kernelopts=root=/dev/mapper/rhel_ibm--root'
                ' ro console=tty0 console=ttyS0,115200 rd_NO_PLYMOUTH"'
            )

        reporting.create_report([
            reporting.Title('Could not set the kernel arguments for future kernels'),
            reporting.Summary(
                'During the upgrade we needed to modify the kernel command line arguments.'
                ' We were able to change the arguments for the default kernel but we were'
                ' not able to set the arguments as the default for kernels installed in'
                ' the future.'
            ),
            report_hint,
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([
                reporting.Groups.BOOT,
                reporting.Groups.KERNEL,
                reporting.Groups.POST,
            ]),
            reporting.RelatedResource('file', '/etc/kernel/cmdline'),
            reporting.RelatedResource('file', '/proc/cmdline'),
        ])
