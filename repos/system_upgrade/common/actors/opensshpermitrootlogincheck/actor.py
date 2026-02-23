from leapp import reporting
from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.opensshpermitrootlogincheck import global_value
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api
from leapp.models import OpenSshConfig, Report
from leapp.reporting import create_report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

COMMON_REPORT_TAGS = [
    reporting.Groups.AUTHENTICATION,
    reporting.Groups.SECURITY,
    reporting.Groups.NETWORK,
    reporting.Groups.SERVICES
]

COMMON_RESOURCES = [
    reporting.RelatedResource('package', 'openssh-server'),
    reporting.RelatedResource('file', '/etc/ssh/sshd_config')
]


class OpenSshPermitRootLoginCheck(Actor):
    """
    OpenSSH no longer allows root logins with password.

    Check the values of PermitRootLogin in OpenSSH server configuration file
    and warn about potential issues after upgrade to the next major version of RHEL.

    The RHEL8 still provided default configuration that allowed root logins,
    which can lead to possible unwanted changes during the upgrade
    """
    name = 'openssh_permit_root_login'
    consumes = (OpenSshConfig, )
    produces = (Report, )
    tags = (ChecksPhaseTag, IPUWorkflowTag, )

    def process(self):
        openssh_messages = self.consume(OpenSshConfig)
        config = next(openssh_messages, None)
        if list(openssh_messages):
            api.current_logger().warning('Unexpectedly received more than one OpenSshConfig message.')
        if not config:
            raise StopActorExecutionError(
                'Could not check openssh configuration', details={'details': 'No OpenSshConfig facts found.'}
            )

        if get_source_major_version() == '8':
            self.process8to9(config)
        elif int(get_source_major_version()) >= 9:
            pass
        else:
            api.current_logger().warning('Unknown source major version: {}'.format(get_source_major_version()))

    @staticmethod
    def process8to9(config):
        # RHEL8 default sshd configuration file is not modified: It will get replaced by rpm and
        # root will no longer be able to connect through ssh. This will probably result in many
        # false positives so it will have to be waived a lot
        if not config.modified:
            create_report([
                reporting.Title('Possible problems with remote login using root account'),
                reporting.Summary(
                    'OpenSSH configuration file will get updated to RHEL9 '
                    'version, no longer allowing root login with password. '
                    'It is a good practice to use non-root administrative '
                    'user and non-password authentications, but if you rely '
                    'on the remote root login, this change can lock you out '
                    'of this system.'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups(COMMON_REPORT_TAGS),
                reporting.Remediation(
                    hint='If you depend on remote root logins using passwords, '
                         'consider setting up a different user for remote '
                         'administration or adding a comment into the '
                         'sshd_config next to the "PermitRootLogin yes" directive '
                         'to prevent rpm replacing it during the upgrade.'
                ),
                reporting.ExternalLink(
                    url='https://access.redhat.com/solutions/7003083',
                    title='Why Leapp Preupgrade for RHEL 8 to 9 getting '
                          '"Possible problems with remote login using root account" ?'
                ),
                reporting.Groups([reporting.Groups.INHIBITOR])
            ] + COMMON_RESOURCES)
        # If the configuration is modified and contains any directive allowing
        # root login (which is in default configuration), we are upgrading to
        # RHEL9 keeping the old "security policy", which might keep the root
        # login unexpectedly open. This might be just high priority warning
        if global_value(config, 'prohibit-password') == 'yes':
            create_report([
                reporting.Title('Remote root logins globally allowed using password'),
                reporting.Summary(
                    'RHEL9 no longer allows remote root logins, but the '
                    'server configuration explicitly overrides this default. '
                    'The configuration file will not be updated and root is '
                    'still going to be allowed to login with password. '
                    'This is not recommended and considered as a security risk.'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups(COMMON_REPORT_TAGS),
                reporting.Remediation(
                    hint='If you depend on remote root logins using passwords, '
                         'consider setting up a different user for remote '
                         'administration. Otherwise you can ignore this message.'
                )
            ] + COMMON_RESOURCES)
