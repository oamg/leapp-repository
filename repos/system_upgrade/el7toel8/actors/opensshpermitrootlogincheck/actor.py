from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.opensshpermitrootlogincheck import semantics_changes
from leapp.models import Report, OpenSshConfig
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import api
from leapp.reporting import create_report
from leapp import reporting


COMMON_REPORT_GROUPS = [
    reporting.Groups.AUTHENTICATION,
    reporting.Groups.SECURITY,
    reporting.Groups.NETWORK,
    reporting.Groups.SERVICES
]


class OpenSshPermitRootLoginCheck(Actor):
    """
    OpenSSH no longer allows root logins with password.

    Check the values of PermitRootLogin in OpenSSH server configuration file
    and warn about potential issues after update.
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

        resources = [
            reporting.RelatedResource('package', 'openssh-server'),
            reporting.RelatedResource('file', '/etc/ssh/sshd_config')
        ]
        if not config.permit_root_login:
            # TODO find out whether the file was modified and will be
            # replaced by the update. If so, this message is bogus
            create_report([
                reporting.Title('Possible problems with remote login using root account'),
                reporting.Summary(
                    'OpenSSH configuration file does not explicitly state '
                    'the option PermitRootLogin in sshd_config file, '
                    'which will default in RHEL8 to "prohibit-password".'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups(COMMON_REPORT_GROUPS + [reporting.Groups.INHIBITOR]),
                reporting.Remediation(
                    hint='If you depend on remote root logins using '
                         'passwords, consider setting up a different '
                         'user for remote administration or adding '
                         '"PermitRootLogin yes" to sshd_config.'
                ),
            ] + resources)

        # Check if there is at least one PermitRootLogin other than "no"
        # in match blocks (other than Match All).
        # This usually means some more complicated setup depending on the
        # default value being globally "yes" and being overwritten by this
        # match block
        if semantics_changes(config):
            create_report([
                reporting.Title('OpenSSH configured to allow root login'),
                reporting.Summary(
                    'OpenSSH is configured to deny root logins in match '
                    'blocks, but not explicitly enabled in global or '
                    '"Match all" context. This update changes the '
                    'default to disable root logins using paswords '
                    'so your server migth get inaccessible.'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups(COMMON_REPORT_GROUPS + [reporting.Groups.INHIBITOR]),
                reporting.Remediation(
                    hint='Consider using different user for administrative '
                         'logins or make sure your configration file '
                         'contains the line "PermitRootLogin yes" '
                         'in global context if desired.'
                ),
            ] + resources)
