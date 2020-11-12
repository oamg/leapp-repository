from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.models import Report, KernelCmdline
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag
from leapp import reporting


class CheckFips(Actor):
    """
    Inhibit upgrade if FIPS is detected as enabled.
    """

    name = 'check_fips'
    consumes = (KernelCmdline,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        cmdline = next(self.consume(KernelCmdline), None)
        if not cmdline:
            raise StopActorExecutionError('Cannot check FIPS state due to missing command line parameters',
                                          details={'Problem': 'Did not receive a message with kernel command '
                                                              'line parameters (KernelCmdline)'})
        for parameter in cmdline.parameters:
            if parameter.key == 'fips' and parameter.value == '1':
                title = 'Cannot upgrade a system with FIPS mode enabled'
                summary = 'Leapp has detected that FIPS is enabled on this system. ' \
                          'In-place upgrade of systems in FIPS mode is currently unsupported.'
                reporting.create_report([
                    reporting.Title(title),
                    reporting.Summary(summary),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.INHIBITOR]),
                ])
