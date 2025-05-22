from leapp.actors import Actor
from leapp.libraries.actor import scankernelcmdline
from leapp.libraries.stdlib import run
from leapp.models import KernelCmdline
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
        cmdline_input = run(['cat', '/proc/cmdline'])['stdout'].strip()
        scankernelcmdline.parse_cmdline_input(cmdline_input)
