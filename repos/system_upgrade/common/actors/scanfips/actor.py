from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.models import FIPSInfo, KernelCmdline
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanFIPS(Actor):
    """
    Determine whether the source system has FIPS enabled.
    """

    name = 'scan_fips'
    consumes = (KernelCmdline,)
    produces = (FIPSInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        cmdline = next(self.consume(KernelCmdline), None)
        if not cmdline:
            raise StopActorExecutionError('Cannot check FIPS state due to missing command line parameters',
                                          details={'Problem': 'Did not receive a message with kernel command '
                                                              'line parameters (KernelCmdline)'})

        for parameter in cmdline.parameters:
            if parameter.key == 'fips' and parameter.value == '1':
                self.produce(FIPSInfo(is_enabled=True))
                return
        self.produce(FIPSInfo(is_enabled=False))
