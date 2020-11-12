from leapp.actors import Actor
from leapp.libraries.actor import checkbrltty
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM, BrlttyMigrationDecision
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

related = [reporting.RelatedResource('package', 'brltty')]


class CheckBrltty(Actor):
    """
    Check if brltty is installed, check whether configuration update is needed.
    """

    name = 'check_brltty'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report, BrlttyMigrationDecision,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRedHatSignedRPM, 'brltty'):
            create_report([
                reporting.Title('Brltty has incompatible changes in the next major version'),
                reporting.Summary(
                    'The --message-delay brltty option has been renamed to --message-timeout.\n'
                    'The -U [--update-interval=] brltty option has been removed.'
                ),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Groups([reporting.Groups.ACCESSIBILITY]),
                reporting.Remediation(
                    hint='Please update your scripts to be compatible with the changes.'
                )
            ] + related)

            (migrate_file, migrate_bt, migrate_espeak,) = checkbrltty.check_for_unsupported_cfg()
            report_summary = ''
            if migrate_bt:
                report_summary = 'Unsupported aliases for bluetooth devices (\'bth:\' and \'bluez:\') will be '
                report_summary += 'renamed to \'bluetooth:\'.'
            if migrate_espeak:
                if report_summary:
                    report_summary += '\n'
                report_summary += 'eSpeak speech driver is no longer supported, it will be switched to eSpeak-NG.'
            if report_summary:
                create_report([
                    reporting.Title('brltty configuration will be migrated'),
                    reporting.Summary(report_summary),
                    reporting.Severity(reporting.Severity.LOW),
                    reporting.Groups([reporting.Groups.ACCESSIBILITY]),
                ] + related)

                self.produce(BrlttyMigrationDecision(migrate_file=migrate_file, migrate_bt=migrate_bt,
                                                     migrate_espeak=migrate_espeak))
