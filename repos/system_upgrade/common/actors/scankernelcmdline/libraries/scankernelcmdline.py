from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import KernelCmdline, KernelCmdlineArg


def get_cmdline_input():
    try:
        cmdline_input = run(['cat', '/proc/cmdline'])['stdout'].strip()
        return cmdline_input
    except (OSError, CalledProcessError):
        api.current_logger().debug('Executing `cat /proc/cmdline` failed', exc_info=True)
    return ''


def parse_cmdline_input():
    cmdline = get_cmdline_input()
    parameters = []
    for parameter in cmdline.split(' '):
        if '=' in parameter:
            kv = parameter.split('=', 1)
            parameters.append(KernelCmdlineArg(key=kv[0], value=kv[1]))
        else:
            parameters.append(KernelCmdlineArg(key=parameter))
    api.produce(KernelCmdline(parameters=parameters))
