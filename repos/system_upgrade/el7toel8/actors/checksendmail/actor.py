from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.libraries.common.rpms import has_package
from leapp.libraries.common.tcpwrappersutils import config_applies_to_daemon
from leapp.models import InstalledRedHatSignedRPM, SendmailMigrationDecision, TcpWrappersFacts
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


COMMON_REPORT_TAGS = [reporting.Tags.SERVICES, reporting.Tags.EMAIL]

related = [
    reporting.RelatedResource('file', f) for f in library.get_conf_files()
] + [reporting.RelatedResource('package', 'sendmail')]


class CheckSendmail(Actor):
    """
    Check if sendmail is installed, check whether configuration update is needed, inhibit upgrade if TCP wrappers
    are used.
    """

    name = 'check_sendmail'
    consumes = (InstalledRedHatSignedRPM, TcpWrappersFacts,)
    produces = (Report, SendmailMigrationDecision,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if not has_package(InstalledRedHatSignedRPM, 'sendmail'):
            return

        if config_applies_to_daemon(next(self.consume(TcpWrappersFacts)), 'sendmail'):
            create_report([
                reporting.Title('TCP wrappers support removed in the next major version'),
                reporting.Summary(
                    'TCP wrappers are legacy host-based ACL (Access Control List) system '
                    'which has been removed in the next major version of RHEL.'
                ),
                reporting.Remediation(
                    hint='Please migrate from TCP wrappers to some other access control mechanism and delete '
                         'sendmail from the /etc/hosts.[allow|deny].'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Tags(COMMON_REPORT_TAGS + [reporting.Tags.NETWORK]),
                reporting.Flags([reporting.Flags.INHIBITOR])
            ] + related)

            return
        migrate_files = library.check_files_for_compressed_ipv6()
        if migrate_files:
            create_report([
                reporting.Title('sendmail configuration will be migrated'),
                reporting.Summary(
                    'IPv6 addresses will be uncompressed, check all IPv6 addresses in all sendmail '
                    'configuration files for correctness.'
                ),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Tags(COMMON_REPORT_TAGS)
            ] + related)

            self.produce(SendmailMigrationDecision(migrate_files=migrate_files))
        else:
            self.log.info('The sendmail configuration seems compatible - it won\'t be migrated.')
