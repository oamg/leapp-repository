import itertools
import os
import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture, get_env
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import (
    BootContent,
    KernelCmdline,
    KernelCmdlineArg,
    LateTargetKernelCmdlineArgTasks,
    LiveImagePreparationInfo,
    LiveModeArtifacts,
    LiveModeConfig,
    TargetKernelCmdlineArgTasks,
    UpgradeKernelCmdlineArgTasks
)


def collect_upgrade_kernel_args(livemode_enabled):
    args = {
        'enforcing': '0',
        'rd.plymouth': '0',
        'plymouth.enable': '0'
    }

    if get_env('LEAPP_DEBUG', '0') == '1':
        args['debug'] = None

    if get_env('LEAPP_DEVEL_INITRAM_NETWORK') in ('network-manager', 'scripts'):
        args['ip'] = 'dhcp'
        args['rd.neednet'] = '1'

    if livemode_enabled:
        livemode_args = construct_cmdline_args_for_livemode()
        args.update(livemode_args)

    upgrade_kernel_args = collect_set_of_kernel_args_from_msgs(UpgradeKernelCmdlineArgTasks, 'to_add')
    args.update(upgrade_kernel_args)

    return set(args.items())


def collect_undesired_args(livemode_enabled):
    args = {}
    if livemode_enabled:
        args = dict(zip(('ro', 'rhgb', 'quiet'), itertools.repeat(None)))
        args['rd.lvm.lv'] = _get_rdlvm_arg_values()

    return set(args.items())


def format_grubby_args_from_args_set(args_dict):
    """ Format the given args set in a form required by grubby's --args. """

    def fmt_single_arg(arg_pair):
        key, value = arg_pair
        if not value:
            return str(key)
        return '{key}={value}'.format(key=key, value=value)

    def flatten_arguments(arg_pair):
        """ Expand multi-valued values into an iterable (key, value1), (key, value2) """
        key, value = arg_pair
        if isinstance(value, (tuple, list)):
            # value is multi-valued (a tuple of values)
            for value_elem in value:  # yield from is not available in python2.7
                yield (key, value_elem)
        else:
            yield (key, value)  # Just a single (key, value) pair

    arg_sequence = itertools.chain(*(flatten_arguments(arg_pair) for arg_pair in args_dict))

    # Sorting should be fine as only values can be None, but we cannot have a (key, None) and (key, value) in
    # the dictionary at the same time.
    cmdline_pieces = (fmt_single_arg(arg_pair) for arg_pair in sorted(arg_sequence))
    cmdline = ' '.join(cmdline_pieces)

    return cmdline


def figure_out_commands_needed_to_add_entry(kernel_path, initramfs_path, args_to_add, args_to_remove):
    boot_entry_modification_commands = []

    args_to_add_str = format_grubby_args_from_args_set(args_to_add)

    create_entry_cmd = [
        '/usr/sbin/grubby',
        '--add-kernel', '{0}'.format(kernel_path),
        '--initrd', '{0}'.format(initramfs_path),
        '--title', 'RHEL-Upgrade-Initramfs',
        '--copy-default',
        '--make-default',
        '--args', args_to_add_str
    ]
    boot_entry_modification_commands.append(create_entry_cmd)

    # We need to update root= param separately, since we cannot do it during --add-kernel with --copy-default.
    # This is likely a bug in grubby.
    root_param_value = dict(args_to_add).get('root', None)
    if root_param_value:
        enforce_root_param_for_the_entry_cmd = [
            '/usr/sbin/grubby',
            '--update-kernel', kernel_path,
            '--args', 'root={0}'.format(root_param_value)
        ]
        boot_entry_modification_commands.append(enforce_root_param_for_the_entry_cmd)

    if args_to_remove:
        args_to_remove_str = format_grubby_args_from_args_set(args_to_remove)
        remove_undesired_args_cmd = [
            '/usr/sbin/grubby',
            '--update-kernel', kernel_path,
            '--remove-args', args_to_remove_str
        ]
        boot_entry_modification_commands.append(remove_undesired_args_cmd)
    return boot_entry_modification_commands


def collect_set_of_kernel_args_from_msgs(msg_type, arg_list_field_name):
    cmdline_modification_msgs = api.consume(msg_type)
    lists_of_args_to_add = (getattr(msg, arg_list_field_name, []) for msg in cmdline_modification_msgs)
    args = itertools.chain(*lists_of_args_to_add)
    return set((arg.key, arg.value) for arg in args)


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
        api.produce(LateTargetKernelCmdlineArgTasks(to_remove=args_sorted))


def add_boot_entry(configs=None):
    kernel_dst_path, initram_dst_path = get_boot_file_paths()

    _remove_old_upgrade_boot_entry(kernel_dst_path, configs=configs)

    livemode_enabled = next(api.consume(LiveImagePreparationInfo), None) is not None

    # We have to keep the desired and unwanted args separate and modify cmline in two separate grubby calls. Merging
    # these sets and trying to execute only a single command would leave the unwanted cmdline args present  if they
    # are present on the original system.
    added_cmdline_args = collect_upgrade_kernel_args(livemode_enabled)
    undesired_cmdline_args = collect_undesired_args(livemode_enabled)

    commands_to_run = figure_out_commands_needed_to_add_entry(kernel_dst_path,
                                                              initram_dst_path,
                                                              args_to_add=added_cmdline_args,
                                                              args_to_remove=undesired_cmdline_args)

    def run_commands_adding_entry(extra_command_suffix=None):
        if not extra_command_suffix:
            extra_command_suffix = []
        for command in commands_to_run:
            run(command + extra_command_suffix)

    try:
        if configs:
            for config in configs:
                run_commands_adding_entry(extra_command_suffix=['-c', config])
        else:
            run_commands_adding_entry(extra_command_suffix=None)

        if architecture.matches_architecture(architecture.ARCH_S390X):
            # on s390x we need to call zipl explicitly because of issue in grubby,
            # otherwise the new boot entry will not be set as default
            # See https://bugzilla.redhat.com/show_bug.cgi?id=1764306
            run(['/usr/sbin/zipl'])

        effective_upgrade_kernel_args = added_cmdline_args - undesired_cmdline_args
        emit_removal_of_args_meant_only_for_upgrade_kernel(effective_upgrade_kernel_args)

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


def local_os_stat(path):
    """ Local wrapper around os.stat so we can safely mock it in tests. """
    return os.stat(path)


def _get_device_uuid(path):
    """
    Find the UUID of a device in which the given path is located.
    """
    while not os.path.ismount(path):
        path = os.path.dirname(path)

    needle_dev_id = local_os_stat(path).st_dev

    for uuid in os.listdir('/dev/disk/by-uuid'):
        uuid_fullpath = os.path.join('/dev/disk/by-uuid/', uuid)
        dev_path = os.readlink(uuid_fullpath)

        # The link target is likely relative to the UUID_fullpath, e.g., ../../dm-1.
        # Joining it will '/dev/disk/by-uuid' will resolve the relative path.
        # If dev_path is absolute it returns dev_path.
        dev_path = os.path.join('/dev/disk/by-uuid', dev_path)
        dev_path = os.path.abspath(dev_path)

        dev_id = local_os_stat(dev_path).st_rdev
        if dev_id == needle_dev_id:
            return uuid

    return None


def _get_rdlvm_arg_values():
    # should we not check args returned by grubby instead?
    cmdline_msg = next(api.consume(KernelCmdline), None)

    if not cmdline_msg:
        raise StopActorExecutionError('Did not receive any KernelCmdline arguments.')

    rd_lvm_values = sorted(arg.value for arg in cmdline_msg.parameters if arg.key == 'rd.lvm.lv')
    api.current_logger().debug('Collected the following rd.lvm.lv args that are undesired for the squashfs: %s',
                               rd_lvm_values)

    return rd_lvm_values


def construct_cmdline_args_for_livemode():
    """
    Prepare cmdline parameters for the live mode
    """
    # boot locally by default

    livemode_config = next(api.consume(LiveModeConfig), None)
    if not livemode_config:
        raise StopActorExecutionError('Did not receive any livemode configuration message although it is enabled.')

    livemode_artifacts = next(api.consume(LiveModeArtifacts), None)
    if not livemode_artifacts:
        raise StopActorExecutionError('Did not receive any livemode artifacts message although it is enabled.')

    liveimg_filename = os.path.basename(livemode_artifacts.squashfs_path)
    dir_path_containing_liveimg = os.path.dirname(livemode_artifacts.squashfs_path)

    args = {'rw': None}

    # if an URL is defined, boot over the network (http, nfs, ftp, ...)
    if livemode_config.url_to_load_squashfs_from:
        args['root'] = 'live:{}'.format(livemode_config.url_to_load_squashfs_from)
    else:
        args['root'] = 'live:UUID={}'.format(_get_device_uuid(dir_path_containing_liveimg))
        args['rd.live.dir'] = dir_path_containing_liveimg
        args['rd.live.squashimg'] = liveimg_filename

    if livemode_config.dracut_network:
        network_fragments = livemode_config.dracut_network.split('=', 1)

        # @Todo(mhecko): verify this during config scan
        if len(network_fragments) == 1 or network_fragments[0] != 'ip':
            msg = ('The livemode dracut_network configuration value is incorrect - it does not '
                   'have the form of a key=value cmdline arg: `{0}`.')
            msg = msg.format(livemode_config.dracut_network)

            api.current_logger().error(msg)
            raise StopActorExecutionError('Livemode is not configured correctly.', details={'details': msg})

        args['ip'] = network_fragments[1]
        args['rd.needsnet'] = '1'

    autostart_state = '1' if livemode_config.autostart_upgrade_after_reboot else '0'
    args['upgrade.autostart'] = autostart_state

    if livemode_config.capture_upgrade_strace_into:
        args['upgrade.strace'] = livemode_config.capture_upgrade_strace_into

    api.current_logger().info('The use of live mode image implies the following cmdline args: %s', args)

    return args
