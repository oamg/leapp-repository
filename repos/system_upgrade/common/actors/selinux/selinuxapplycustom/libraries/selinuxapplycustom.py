import os
import re
import shutil

from leapp.libraries.stdlib import api, CalledProcessError, run

BACKUP_DIRECTORY = '/var/lib/selinux/leapp-backup'


def list_selinux_modules():
    """
    Produce list of SELinux policy modules

    Returns list of tuples (name,priority)
    """
    try:
        semodule = run(['semodule', '-lfull'], split=True)
    except CalledProcessError:
        api.current_logger().warning('Cannot get list of selinux modules')
        return []

    modules = []
    for module in semodule.get('stdout', []):
        # Matching line such as "100 zebra             pp"
        #                       "400 virt_supplementary pp disabled"
        # "<priority> <module name> <module type - pp/cil> [disabled]"
        m = re.match(r'([0-9]+)\s+([\w-]+)\s+([\w-]+)(?:\s+([\w]+))?\s*\Z', module)
        if not m:
            # invalid output of "semodule -lfull"
            api.current_logger().warning('Invalid output of "semodule -lfull": {}'.format(module))
            continue
        modules.append((m.group(2), m.group(1)))

    return modules


# determine which (if any) udica templates where installed and install their new versions
def install_udica_templates(templates):
    if not templates:
        return

    command = ['semodule']
    for module in templates:
        command.extend(
            [
                '-X',
                str(module.priority),
                '-i',
                '/usr/share/udica/templates/{}.cil'.format(module.name)
            ]
        )

    try:
        run(command)
    except CalledProcessError as e:
        api.current_logger().warning('Error installing udica templates: {}'.format(e.stderr))


# move given file to the backup directory so that users can access it after the upgrade
def back_up_failed(module_path):
    # make sure the backup dir exists
    if not os.path.isdir(BACKUP_DIRECTORY):
        try:
            os.mkdir(BACKUP_DIRECTORY)
        except OSError:
            api.current_logger().warning('Failed to create backup directory!')
            return
    try:
        shutil.move(module_path, BACKUP_DIRECTORY)
    except OSError:
        api.current_logger().warning('Failed to back-up: {}!'.format(module_path))
        return
