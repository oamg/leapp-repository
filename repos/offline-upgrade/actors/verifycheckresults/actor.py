from leapp.actors import Actor
from leapp.libraries.actor import report
from leapp.models import CheckResult
from leapp.tags import ReportPhaseTag, IPUWorkflowTag


class VerifyCheckResults(Actor):
    name = 'verify_check_results'
    description = 'Verify results, stop process if error and generate report.'
    consumes = (CheckResult,)
    produces = ()
    tags = (ReportPhaseTag, IPUWorkflowTag)

    def process(self):
        results = [msg for msg in self.consume(CheckResult)]
        errors = [msg for msg in results if msg.severity == 'Error']

        report_file = '/tmp/leapp-report.txt'
        error = report.generate_report(results, report_file)
        if error:
            self.report_error('Report Error: ' + error)
        else:
            self.log.info('Generated report at ' + report_file)

        if errors:
            for e in errors:
                self.report_error('%s: %s: %s' % (e.severity, e.result, e.summary))

            self.report_error('Ending process due to errors found during checks')
