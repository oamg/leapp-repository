from leapp.actors import Actor
from leapp.libraries.actor import migratebrltty
from leapp.models import BrlttyMigrationDecision
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MigrateBrltty(Actor):
    """
    Migrate brltty configuration files.
    """

    name = 'migrate_brltty'
    consumes = (BrlttyMigrationDecision,)
    produces = (Report,)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        for decision in self.consume(BrlttyMigrationDecision):
            report_summary = ''
            migratebrltty.migrate_file(decision.migrate_file, decision.migrate_bt, decision.migrate_espeak)
            if decision.migrate_bt:
                report_summary = 'Unsupported aliases for bluetooth devices (\'bth:\' and \'bluez:\') was '
                report_summary += 'renamed to \'bluetooth:\' in {}'
                report_summary = report_summary.format(', '.join(decision.migrate_file))
            if decision.migrate_espeak:
                if report_summary:
                    report_summary += '\n'
                report_summary += 'eSpeak speech driver was switched to eSpeak-NG in {}'
                report_summary = report_summary.format(', '.join(decision.migrate_file))
            if decision.migrate_bt or decision.migrate_espeak:
                create_report([
                    reporting.Title('brltty configuration files migrated'),
                    reporting.Summary(report_summary),
                    reporting.Severity(reporting.Severity.LOW),
                    reporting.Groups([reporting.Groups.TOOLS, reporting.Groups.ACCESSIBILITY]),
                    reporting.RelatedResource('package', 'brltty')
                ])
