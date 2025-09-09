import os
import re

from leapp.libraries.stdlib import api


def _process_knownhosts(line: str) -> str:
    if re.search(r'^\s*#?\s*ProxyCommand\s+(/usr/bin/)?sss_ssh_knownhostsproxy', line) is not None:
        # Update the line, leaving intact any # and any --domain/-d parameter
        line = line.replace('ProxyCommand', 'KnownHostsCommand')
        line = line.replace('sss_ssh_knownhostsproxy', 'sss_ssh_knownhosts')
        line = line.replace('--port=', '')
        line = line.replace('--port', '')
        line = line.replace('-p=', '')
        line = line.replace('-p', '')
        line = line.replace('%p', '')
        line = line.replace('%h', '%H')

    return line


def _process_enable_svc(line: str) -> str:
    if re.search(r'^\s*#?\s*services\s*=', line) is not None:
        if re.search(r'=\s*(.+,)?\s*ssh\s*(,.+)?\s*$', line) is None:
            line = line.rstrip()
            line += (',' if line[-1] != '=' else '') + 'ssh\n'

    return line


def _update_file(filename, process_function):
    newname = '{}.leappnew'.format(filename)
    oldname = '{}.leappsave'.format(filename)
    try:
        with open(filename, 'r') as input_file, open(newname, 'w') as output_file:
            istat = os.fstat(input_file.fileno())
            os.fchmod(output_file.fileno(), istat.st_mode)
            for line in input_file:
                try:
                    output_file.write(process_function(line))
                except OSError as e:
                    api.current_logger().warning('Failed to write to {}'.format(newname), details={'details': str(e)})

    except OSError as e:
        try:
            os.unlink(newname)
        except FileNotFoundError:
            pass
        api.current_logger().error('Failed to access the required files', details={'details': str(e)})

    # Let's make sure the old configuration is preserved if something goes wrong
    os.replace(filename, oldname)
    os.replace(newname, filename)
    os.unlink(oldname)


def _update_ssh_config(filename: str):
    _update_file(filename, _process_knownhosts)


def _enable_svc(filename):
    _update_file(filename, _process_enable_svc)


def update_config(model):
    if not model:
        return

    # If sss_ssh_knownhostsproxy was not configured, there is nothing to do
    if not model.ssh_config_files:
        return

    for file in model.ssh_config_files:
        _update_ssh_config(file)

    for file in model.sssd_config_files:
        _enable_svc(file)
