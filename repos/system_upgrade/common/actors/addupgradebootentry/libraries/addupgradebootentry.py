import itertools
import os
import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import (
    BootContent,
    KernelCmdline,
    KernelCmdlineArg,
    TargetKernelCmdlineArgTasks,
    UpgradeKernelCmdlineArgTasks
)


def collect_set_of_kernel_args_from_msgs(msg_type, arg_list_field_name):
    cmdline_modification_msgs = api.consume(msg_type)
    lists_of_args_to_add = (getattr(msg, arg_list_field_name, []) for msg in cmdline_modification_msgs)
    args = itertools.chain(*lists_of_args_to_add)
    return set((arg.key, arg.value) for arg in args)


def fmt_kernel_args(args):
    def fmt_arg(arg):
        if arg[1]:
            return '{0}={1}'.format(*arg)
        return arg[0]

    args_str = ' '.join(fmt_arg(arg) for arg in sorted(args, key=lambda arg: arg[0]))
    return args_str


def emit_removal_of_args_meant_only_for_upgrade_kernel(added_upgrade_kernel_args):
    """
    Emit message requesting removal of upgrade kernel args that should not be on the target kernel.

    Target kernel args are created by copying the args of the booted (upgrade) kernel. Therefore,
    we need to explicitly modify the target kernel cmdline, removing what should not have been copied.
    """
    target_args_to_add = collect_set_of_kernel_args_from_msgs(TargetKernelCmdlineArgTasks, 'to_add')
    actual_kernel_args = collect_set_of_kernel_args_from_msgs(KernelCmdline, 'parameters')

    # actual_kernel_args should not be changed during upgrade, unless explicitly removed by
    # TargetKernelCmdlineArgTasks.to_remove, but that is handled by some other upgrade component. We just want
    # to make sure we remove what was not on the source system and that we don't overwrite args to be added to target.
    args_not_present_on_target_kernel = added_upgrade_kernel_args - actual_kernel_args - target_args_to_add

    # We remove only what we've added and what will not be already removed by someone else.
    args_to_remove = [KernelCmdlineArg(key=arg[0], value=arg[1]) for arg in args_not_present_on_target_kernel]

    if args_to_remove:
        msg = ('Following upgrade kernel args were added, but they should not be present '
               'on target cmdline: `%s`, requesting removal.')
        api.current_logger().info(msg, args_not_present_on_target_kernel)
        args_sorted = sorted(args_to_remove, key=lambda arg: arg.key)
        api.produce(TargetKernelCmdlineArgTasks(to_remove=args_sorted))


def add_boot_entry(configs=None):
    enable_network = os.getenv('LEAPP_DEVEL_INITRAM_NETWORK') in ('network-manager', 'scripts')
    ip_arg = 'ip=dhcp rd.neednet=1' if enable_network else ''
    kernel_dst_path, initram_dst_path = get_boot_file_paths()

    additional_args = collect_set_of_kernel_args_from_msgs(UpgradeKernelCmdlineArgTasks, 'to_add')

    # Manage hardcoded upgrade kernel args that should be applied only to the upgrade kernel too
    if os.getenv('LEAPP_DEBUG', '0') == '1':
        additional_args.add(('debug', None))
    additional_args.add(('enforcing', '0'))

    additional_args_str = fmt_kernel_args(additional_args)
    api.current_logger().info('Additional kernel cmdline args for the upgrade kernel: %s', additional_args_str)

    all_args = '{NET} {additional_args} rd.plymouth=0 plymouth.enable=0'.format(
        NET=ip_arg,
        additional_args=additional_args_str
    ).strip()

    _remove_old_upgrade_boot_entry(kernel_dst_path, configs=configs)
    try:
        cmd = [
            '/usr/sbin/grubby',
            '--add-kernel', '{0}'.format(kernel_dst_path),
            '--initrd', '{0}'.format(initram_dst_path),
            '--title', 'RHEL-Upgrade-Initramfs',
            '--copy-default',
            '--make-default',
            '--args', all_args
        ]
        if configs:
            for config in configs:
                run(cmd + ['-c', config])
        else:
            run(cmd)

        if architecture.matches_architecture(architecture.ARCH_S390X):
            # on s390x we need to call zipl explicitly because of issue in grubby,
            # otherwise the new boot entry will not be set as default
            # See https://bugzilla.redhat.com/show_bug.cgi?id=1764306
            run(['/usr/sbin/zipl'])

        emit_removal_of_args_meant_only_for_upgrade_kernel(additional_args)

    except CalledProcessError as e:
        raise StopActorExecutionError(
           'Cannot configure bootloader.',
           details={'details': '{}: {}'.format(str(e), e.stderr)}
        )


def _remove_old_upgrade_boot_entry(kernel_dst_path, configs=None):
    """
    Remove entry referring to the upgrade kernel.

    We have to ensure there are no duplicit boot entries. Main reason is crash
    of zipl when duplicit entries exist.
    """
    cmd = [
        '/usr/sbin/grubby',
        '--remove-kernel', '{0}'.format(kernel_dst_path)
    ]
    try:
        if configs:
            for config in configs:
                run(cmd + ['-c', config])
        else:
            run(cmd)
    except CalledProcessError:
        # TODO(pstodulk): instead of this, check whether the entry exists or not
        # so no warning of problem is reported (info log could be present if the
        # entry is missing.
        api.current_logger().warning(
            'Could not remove {} entry. May be ignored if the entry did not exist.'.format(kernel_dst_path)
        )


def get_boot_file_paths():
    boot_content_msgs = api.consume(BootContent)
    boot_content = next(boot_content_msgs, None)
    if list(boot_content_msgs):
        api.current_logger().warning('Unexpectedly received more than one BootContent message.')
    if not boot_content:
        raise StopActorExecutionError('Could not create a GRUB boot entry for the upgrade initramfs',
                                      details={'details': 'Did not receive a message about the leapp-provided'
                                                          'kernel and initramfs'})
    # Returning information about kernel hmac file path is needless as it is not used when adding boot entry
    return boot_content.kernel_path, boot_content.initram_path


def write_to_file(filename, content):
    with open(filename, 'w') as f:
        f.write(content)


def fix_grub_config_error(conf_file, error_type):
    with open(conf_file, 'r') as f:
        config = f.read()

    if error_type == 'GRUB_CMDLINE_LINUX syntax':
        # move misplaced '"' to the end
        pattern = r'GRUB_CMDLINE_LINUX=.+?(?=GRUB|\Z)'
        original_value = re.search(pattern, config, re.DOTALL).group()
        parsed_value = original_value.split('"')
        new_value = '{KEY}"{VALUE}"{END}'.format(KEY=parsed_value[0], VALUE=''.join(parsed_value[1:]).rstrip(),
                                                 END=original_value[-1])

        config = config.replace(original_value, new_value)
        write_to_file(conf_file, config)

    elif error_type == 'missing newline':
        write_to_file(conf_file, config + '\n')
