from leapp.actors import Actor
from leapp.libraries.actor import report
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
        inhibitors = [msg for msg in results if 'inhibitor' in msg.flags]
        high_sev_msgs = [msg for msg in results if msg.severity == 'high' and 'inhibitor' not in msg.flags]
        msgs_to_report = inhibitors + high_sev_msgs

        report_file = '/var/log/leapp/leapp-report.txt'
        error = report.generate_report(msgs_to_report, report_file)
        if error:
            self.report_error('Report Error: ' + error)
        else:
            self.log.info('Generated report at ' + report_file)

        if inhibitors:
            for e in inhibitors:
                self.report_error(e.title)

            self.report_error('Ending process due to errors found during checks, see {} for detailed report.'
                              .format(report_file))
