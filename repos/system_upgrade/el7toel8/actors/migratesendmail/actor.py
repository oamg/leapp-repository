from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.libraries.common.reporting import report_generic
from leapp.models import SendmailMigrationDecision
from leapp.reporting import Report
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
            library.migrate_file(f)
        list_separator_fmt = '\n    - '
        report_generic(
            title='sendmail configuration files migrated',
            summary='Uncompressed IPv6 addresses in {}'.format(list_separator_fmt.join(decision.migrate_files)),
            severity='low')
