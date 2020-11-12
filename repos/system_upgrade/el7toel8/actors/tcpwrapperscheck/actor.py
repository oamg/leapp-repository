from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.models import Report, TcpWrappersFacts, InstalledRedHatSignedRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import api
from leapp.libraries.actor.tcpwrapperscheck import config_affects_daemons
from leapp.libraries.common.rpms import create_lookup
from leapp.reporting import create_report
from leapp import reporting

DAEMONS = [
    ("audit", ["auditd"]),
    ("bacula", ["bacula"]),
    ("conserver", ["conserver"]),
    ("cyrus-imapd", ["imap", "pop3", "imaps", "pop3s", "sieve", "lmtp"]),
    ("dovecot", ["imap", "pop3", "imaps", "pop3s", "sieve", "lmtp"]),
    ("nfs-utils", ["mountd", "statd"]),
    ("openssh-server", ["sshd"]),
    ("proftpd", ["proftpd"]),
    ("quota", ["rquotad"]),
    ("rpcbind", ["rpcbind"]),
    # ("sendmail", ["sendmail"]),  # Handled in CheckSendmail Actor
    ("slapi-nis", ["slapi-nis"]),
    ("socat", ["socat"]),
    ("stunnel", ["stunnel"]),
    ("tftp-server", ["tftpd"]),
    # ("vsftpd", ["vsftpd"]),  # Handled in VsftpdConfigCheck Actor
    ("xinetd", ["xinetd"]),
]


class TcpWrappersCheck(Actor):
    """
    Check the list of packages previously compiled with TCP wrappers support
    and check whether they have some rules configured in
    /etc/hosts.{allow,deny} that are no longer honored by the daemons and
    might make the service more accessible than expected.
    """

    name = 'tcp_wrappers_check'
    consumes = (TcpWrappersFacts, InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        # Consume a single TCP Wrappers message
        tcp_wrappers_messages = self.consume(TcpWrappersFacts)
        tcp_wrappers_facts = next(tcp_wrappers_messages, None)
        if list(tcp_wrappers_messages):
            api.current_logger().warning('Unexpectedly received more than one TcpWrappersFacts message.')
        if not tcp_wrappers_facts:
            raise StopActorExecutionError(
                'Could not check tcp wrappers configuration', details={'details': 'No TcpWrappersFacts found.'}
            )

        # Convert installed packages message to list
        packages = create_lookup(InstalledRedHatSignedRPM, field='items', key='name')

        found_packages = config_affects_daemons(tcp_wrappers_facts, packages, DAEMONS)

        if found_packages:
            create_report([
                reporting.Title('TCP Wrappers configuration affects some installed packages'),
                reporting.Summary(
                    'tcp_wrappers support has been removed in RHEL-8. '
                    'There is some configuration affecting installed packages (namely {}) '
                    'in /etc/hosts.deny or /etc/hosts.allow, which '
                    'is no longer going to be effective after update. '
                    'Please migrate it manually.'.format(', '.join(found_packages))
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.ExternalLink(
                    title='Replacing TCP Wrappers in RHEL 8',
                    url='https://access.redhat.com/solutions/3906701'
                ),
                reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.NETWORK, reporting.Groups.INHIBITOR]),
                reporting.RelatedResource('file', '/etc/hosts.allow'),
                reporting.RelatedResource('file', '/etc/hosts.deny'),
                reporting.RelatedResource('package', 'tcp_wrappers')
            ] + [reporting.RelatedResource('package', fp) for fp in found_packages])
