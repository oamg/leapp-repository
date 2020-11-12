from leapp.actors import Actor
from leapp.libraries.actor import migratesendmail
from leapp.models import SendmailMigrationDecision
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MigrateSendmail(Actor):
    """
    Migrate sendmail configuration files.
    """

    name = 'migrate_sendmail'
    consumes = (SendmailMigrationDecision,)
    produces = (Report,)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        decision = next(self.consume(SendmailMigrationDecision), None)
        if not decision or not decision.migrate_files:
            return

        for f in decision.migrate_files:
            migratesendmail.migrate_file(f)
        list_separator_fmt = '\n    - '
        create_report([
            reporting.Title('sendmail configuration files migrated'),
            reporting.Summary(
                'Uncompressed IPv6 addresses in {}'.format(list_separator_fmt.join(decision.migrate_files))
            ),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.EMAIL])
        ])
