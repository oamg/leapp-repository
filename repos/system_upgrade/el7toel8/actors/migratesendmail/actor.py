import os

from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.actor import migratesendmail
from leapp.libraries.stdlib import api
from leapp.models import SendmailMigrationDecision
from leapp.reporting import create_report, Report
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

        not_migrated = []
        for f in decision.migrate_files:
            if not os.path.exists(f):
                api.current_logger().error('Cound not migrate file {}, because it does not exist.'.format(f))
                not_migrated.append(f)
            else:
                migratesendmail.migrate_file(f)

        list_separator_fmt = '\n    - '
        title = 'sendmail configuration files migrated'
        summary = 'Uncompressed IPv6 addresses in: {}{}'.format(list_separator_fmt,
                                                                list_separator_fmt.join(decision.migrate_files))
        severity = reporting.Severity.INFO

        if not_migrated:
            title = 'sendmail configuration files not migrated'
            summary = ('Could not migrate the configuration files, which might be caused '
                       'by removal of sendmail package during the upgrade. '
                       'Following files could not be migrated:{}{}').format(list_separator_fmt,
                                                                            list_separator_fmt.join(not_migrated))
            severity = reporting.Severity.MEDIUM

        create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(severity),
            reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.EMAIL])
        ])
