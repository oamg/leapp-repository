from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.libraries.common.reporting import report_with_remediation, report_generic
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM, BrlttyMigrationDecision
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


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
            report_with_remediation(
                title='Brltty has incompatible changes in the next major version',
                summary='The --message-delay brltty option has been renamed to --message-timeout.\n'
                        'The -U [--update-interval=] brltty option has been removed.',
                remediation='Please update your scripts to be compatible with the changes.',
                severity='low')
            (migrate_file, migrate_bt, migrate_espeak) = library.check_for_unsupported_cfg()
            report_summary = ''
            if migrate_bt:
                report_summary = 'Unsupported aliases for bluetooth devices (\'bth:\' and \'bluez:\') will be '
                report_summary += 'renamed to \'bluetooth:\'.'
            if migrate_espeak:
                if report_summary:
                    report_summary += '\n'
                report_summary += 'eSpeak speech driver is no longer supported, it will be switched to eSpeak-NG.'
            if report_summary:
                report_generic(
                    title='brltty configuration will be migrated',
                    summary=report_summary,
                    severity='low')
                self.produce(BrlttyMigrationDecision(migrate_file=migrate_file, migrate_bt=migrate_bt,
                                                     migrate_espeak=migrate_espeak))
            else:
                report_generic(
                    title='brltty configuration will be not migrated',
                    summary='brltty configuration seems to be compatible',
                    severity='low')
