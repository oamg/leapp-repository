from leapp.actors import Actor
from leapp.libraries.stdlib import run
from leapp.models import KernelCmdline, KernelCmdlineArg
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanKernelCmdline(Actor):
    """
    Scan the kernel command line of the booted system.
    """

    name = 'scan_kernel_cmdline'
    consumes = ()
    produces = (KernelCmdline,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        cmdline = run(['cat', '/proc/cmdline'])['stdout'].strip()
        parameters = []
        for parameter in cmdline.split(' '):
            if '=' in parameter:
                kv = parameter.split('=', 1)
                parameters.append(KernelCmdlineArg(key=kv[0], value=kv[1]))
            else:
                parameters.append(KernelCmdlineArg(key=parameter))
        self.produce(KernelCmdline(parameters=parameters))
