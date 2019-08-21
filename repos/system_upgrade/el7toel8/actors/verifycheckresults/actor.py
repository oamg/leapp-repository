from leapp.actors import Actor
from leapp.reporting import Report
from leapp.tags import ReportPhaseTag, IPUWorkflowTag


class VerifyCheckResults(Actor):
    """
    Check all generated results messages and notify user about them.

    A report file containing all messages will be generated, together with log messages displayed
    to the user.
    """

    name = 'verify_check_results'
    consumes = (Report,)
    produces = ()
    tags = (ReportPhaseTag, IPUWorkflowTag)

    def process(self):
        results = list(self.consume(Report))
        for error in [msg for msg in results if 'inhibitor' in msg.report.get('flags', [])]:
            self.report_error(error.report['title'])
