from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.libraries.common.reporting import report_with_remediation, report_generic
from leapp.libraries.common.rpms import has_package
from leapp.libraries.common.tcpwrappersutils import config_applies_to_daemon
from leapp.models import InstalledRedHatSignedRPM, SendmailMigrationDecision, TcpWrappersFacts
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


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
            report_with_remediation(
                title='TCP wrappers support removed in the next major version',
                summary='TCP wrappers are legacy host-based ACL (Access Control List) system '
                        'which has been removed in the next major version of RHEL.',
                remediation='Please migrate from TCP wrappers to some other access control mechanism and delete '
                        'sendmail from the /etc/hosts.[allow|deny].',
                severity='high',
                flags=['inhibitor'])
            return
        migrate_files = library.check_files_for_compressed_ipv6()
        if migrate_files:
            report_generic(
                title='sendmail configuration will be migrated',
                summary='IPv6 addresses will be uncompressed, check all IPv6 addresses in all sendmail '
                        'configuration files for correctness.',
                severity='low')
            self.produce(SendmailMigrationDecision(migrate_files=migrate_files))
        else:
            self.log.info('The sendmail configuration seems compatible - it won\'t be migrated.')
