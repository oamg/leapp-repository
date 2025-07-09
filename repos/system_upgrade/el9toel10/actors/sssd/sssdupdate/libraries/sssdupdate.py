import os

from leapp.exceptions import StopActorExecutionError

def _process_knownhosts(line:str) -> str:
    if 'sss_ssh_knownhostsproxy' in line:
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

def _process_enable_svc(line:str) -> str:
    if 'services' in line:
        line = line.rstrip()
        line += (',' if line[-1] != '=' else '') + 'ssh\n'

    return line

def _update_file(filename, process_function):
    newname = filename + '.new'
    oldname = filename + '.old'
    try:
        with open(filename, 'r') as input:
            istat = os.fstat(input.fileno())
            with open(newname, 'x', ) as output:
                os.fchmod(output.fileno(), istat.st_mode)
                for line in input:
                    try:
                        output.write(process_function(line))
                    except SyntaxError as e:
                        raise StopActorExecutionError(filename + ': ' + e)

    except FileExistsError:
        raise StopActorExecutionError('Temporary file ' + newname + ' already exists')
    except OSError as e:
        try:
            os.unlink(newname)
        except FileNotFoundError:
            pass
        raise StopActorExecutionError(str(e))

    # Let's make sure the old configuration is preserverd if something goes wrong
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
    if len(model.ssh_config_files) == 0:
        return

    for file in model.ssh_config_files:
        _update_ssh_config(file)

    for file in model.sssd_config_files:
        _enable_svc(file)
