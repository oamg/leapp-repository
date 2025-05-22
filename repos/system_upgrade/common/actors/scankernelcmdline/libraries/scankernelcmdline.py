from leapp.libraries.stdlib import api, run
from leapp.models import KernelCmdline, KernelCmdlineArg


def parse_cmdline_input(cmdline):
    parameters = []
    for parameter in cmdline.split(' '):
        if '=' in parameter:
            kv = parameter.split('=', 1)
            parameters.append(KernelCmdlineArg(key=kv[0], value=kv[1]))
        else:
            parameters.append(KernelCmdlineArg(key=parameter))
    api.produce(KernelCmdline(parameters=parameters))

