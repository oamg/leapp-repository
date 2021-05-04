from leapp.actors import Actor
from leapp.libraries.stdlib import run
from leapp.models import KernelCmdline, KernelCmdlineArg
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanKernelCmdline(Actor):
    """
    No documentation has been provided for the scan_kernel_cmdline actor.
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
                kv = parameter.split('=')
                parameters.append(KernelCmdlineArg(key=kv[0], value=kv[1]))
            else:
                parameters.append(KernelCmdlineArg(key=parameter))
        self.produce(KernelCmdline(parameters=parameters))
