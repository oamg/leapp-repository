import os
import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.models import BootContent


def add_boot_entry(configs=None):
    debug = 'debug' if os.getenv('LEAPP_DEBUG', '0') == '1' else ''

    kernel_dst_path, initram_dst_path = get_boot_file_paths()
    try:
        _remove_old_upgrade_boot_entry(kernel_dst_path, configs=configs)
        cmd = [
            '/usr/sbin/grubby',
            '--add-kernel', '{0}'.format(kernel_dst_path),
            '--initrd', '{0}'.format(initram_dst_path),
            '--title', 'RHEL-Upgrade-Initramfs',
            '--copy-default',
            '--make-default',
            '--args', '{DEBUG} enforcing=0 rd.plymouth=0 plymouth.enable=0'.format(DEBUG=debug)
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
    if configs:
        for config in configs:
            run(cmd + ['-c', config])
    else:
        run(cmd)


def get_boot_file_paths():
    boot_content_msgs = api.consume(BootContent)
    boot_content = next(boot_content_msgs, None)
    if list(boot_content_msgs):
        api.current_logger().warning('Unexpectedly received more than one BootContent message.')
    if not boot_content:
        raise StopActorExecutionError('Could not create a GRUB boot entry for the upgrade initramfs',
                                      details={'details': 'Did not receive a message about the leapp-provided'
                                                          'kernel and initramfs'})
    return boot_content.kernel_path, boot_content.initram_path


def write_to_file(filename, content):
    with open(filename, 'w') as f:
        f.write(content)


def fix_grub_config_error(conf_file):
    with open(conf_file, 'r') as f:
        config = f.read()

    # move misplaced '"' to the end
    pattern = r'GRUB_CMDLINE_LINUX=.+?(?=GRUB|\Z)'
    original_value = re.search(pattern, config, re.DOTALL).group()
    parsed_value = original_value.split('"')
    new_value = '{KEY}"{VALUE}"{END}'.format(KEY=parsed_value[0], VALUE=''.join(parsed_value[1:]).rstrip(),
                                             END=original_value[-1])

    config = config.replace(original_value, new_value)

    write_to_file(conf_file, config)
