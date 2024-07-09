import itertools
import os
import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import (
    BootContent,
    KernelCmdlineArg,
    LiveImagePreparationInfo,
    LiveModeArtifacts,
    LiveModeConfigFacts,
    TargetKernelCmdlineArgTasks
)


def collect_boot_args(livemode_enabled):
    args = {
        'enforcing': '0',
        'rd.plymouth': '0',
        'plymouth.enable': '0'
    }

    if os.getenv('LEAPP_DEBUG', '0') == '1':
        args['debug'] = None

    if os.getenv('LEAPP_DEVEL_INITRAM_NETWORK') in ('network-manager', 'scripts'):
        args['ip'] = 'dhcp'
        args['rd.neednet'] = '1'

    if livemode_enabled:
        livemode_args = construct_cmdline_args_for_livemode()
        args.update(livemode_args)

    return args


def collect_undesired_args(livemode_enabled):
    args = {}
    if livemode_enabled:
        args = dict(zip(('ro', 'rhgb', 'quiet'), itertools.repeat(None)))
        args.update(_get_rdlvm_args())
    return args


def format_grubby_args_from_args_dict(args_dict):
    """ Format the given args dictionary in a form required by grubby's --args. """

    def fmt_single_arg(arg_pair):
        key, value = arg_pair
        if value:
            return '{key}={value}'.format(key=key, value=value)
        return str(key)

    return ' '.join(fmt_single_arg(arg_pair) for arg_pair in args_dict.items())


def add_boot_entry(configs=None):
    kernel_dst_path, initram_dst_path = get_boot_file_paths()
    _remove_old_upgrade_boot_entry(kernel_dst_path, configs=configs)

    livemode_enabled = next(api.consume(LiveImagePreparationInfo), None) is None

    cmdline_args = collect_boot_args(livemode_enabled)
    undesired_cmdline_args = collect_undesired_args(livemode_enabled)

    args_to_add_str = format_grubby_args_from_args_dict(cmdline_args)
    args_to_remove_str = format_grubby_args_from_args_dict(undesired_cmdline_args)

    try:
        cmd = [
            '/usr/sbin/grubby',
            '--add-kernel', '{0}'.format(kernel_dst_path),
            '--initrd', '{0}'.format(initram_dst_path),
            '--title', 'RHEL-Upgrade-Initramfs',
            '--copy-default',
            '--make-default',
            '--args', args_to_add_str
        ]

        remove_undesired_args_cmd = [
            '/usr/sbin/grubby',
            '--update-kernel', kernel_dst_path,
            '--remove-args', ' '.join(args_to_remove_str)
        ]

        if configs:
            for config in configs:
                run(cmd + ['-c', config])
                if undesired_cmdline_args:
                    run(remove_undesired_args_cmd + ['-c', config])
        else:
            run(cmd)
            run(remove_undesired_args_cmd)

        if architecture.matches_architecture(architecture.ARCH_S390X):
            # on s390x we need to call zipl explicitly because of issue in grubby,
            # otherwise the new boot entry will not be set as default
            # See https://bugzilla.redhat.com/show_bug.cgi?id=1764306
            run(['/usr/sbin/zipl'])

        if args_to_add_str.get('debug', '0') == '1':
            # The kernelopts for target kernel are generated based on the cmdline used in the upgrade initramfs,
            # therefore, if we enabled debug above, and the original system did not have the debug kernelopt, we
            # need to explicitly remove it from the target os boot entry.
            # NOTE(mhecko): This will also unconditionally remove debug kernelopt if the source system used it.
            api.produce(TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='debug')]))

        # NOTE(mmatuska): This will remove the option even if the source system had it set.
        # However enforcing=0 shouldn't be set persistently anyway.
        api.produce(TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='enforcing', value='0')]))

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


def _get_device_uuid(path):
    """
    Find the UUID of a device in which the given path is located.
    """
    while not os.path.ismount(path):
        path = os.path.dirname(path)

    needle_dev_id = os.stat(path).st_dev

    for uuid in os.listdir('/dev/disk/by-uuid'):
        uuid_fullpath = os.path.join('/dev/disk/by-uuid/', uuid)
        dev_path = os.readlink(uuid_fullpath)
        dev_id = os.stat(dev_path).st_rdev
        if dev_id == needle_dev_id:
            return uuid

    return None


def _get_rdlvm_args():
    # should we not check args returned by grubby instead?
    with open('/proc/cmdline') as f:
        cmdline = f.read().strip().split(' ')

    def into_arg_pair(raw_arg):
        arg_pair = raw_arg.split('=', maxsplit=1)
        if len(arg_pair) == 1:
            return (raw_arg, None)
        return arg_pair

    return {into_arg_pair(arg) for arg in cmdline if arg.startswith('rd.lvm')}


def construct_cmdline_args_for_livemode():
    """
    Prepare cmdline parameters for the live mode
    """
    # boot locally by default

    livemode_config = next(api.consume(LiveModeConfigFacts), None)
    if not livemode_config:
        raise StopActorExecutionError('Did not receive any livemode configuration message although it is enabled.')

    livemode_artifacts = next(api.consume(LiveModeArtifacts), None)
    if not livemode_artifacts:
        raise StopActorExecutionError('Did not receive any livemode artifacts message although it is enabled.')

    liveimg = os.path.basename(livemode_artifacts.squashfs)
    livedir = os.path.dirname(livemode_artifacts.squashfs)

    args = {}

    # if an URL is defined, boot over the network (http, nfs, ftp, ...)
    if livemode_config.url:
        args['root'] = 'live:{}'.format(livemode_config.url)
    else:
        args['root'] = 'live:UUID={}'.format(_get_device_uuid(livedir))
        args['rd.live.dir'] = livedir
        args['rd.live.squashimg'] = liveimg

    if livemode_config.dracut_network:
        network_fragments = livemode_config.dracut_network.split('=', maxsplit=1)

        # @Todo(mhecko): verify this during config scan

        if len(network_fragments) == 1 or network_fragments[0] != 'ip':
            msg = ('The livemode dracut_network configuration value is incorrect - it does not '
                   'have the form of a key-value cmdline arg: `{0}`.')
            msg = msg.format(livemode_config.dracut_network)

            api.current_logger().error(msg)
            raise StopActorExecutionError('Livemode is not configured correctly.', details={'details': msg})

        net_arg_value = network_fragments[1]
        args['ip'] = net_arg_value
        args['rd.needsnet'] = '1'

    autostart_state = '1' if livemode_config.autostart else '0'
    args['upgrade.autostart'] = autostart_state

    if livemode_config.strace:
        args['upgrade.strace'] = livemode_config.strace

    api.current_logger().info('The use of live mode image implies the following cmdline args: %s', args)

    return args
