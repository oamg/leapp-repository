from leapp import reporting
from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.opensshpermitrootlogincheck import semantics_changes
from leapp.libraries.stdlib import api
from leapp.models import OpenSshConfig, Report
from leapp.reporting import create_report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

COMMON_REPORT_TAGS = [
    reporting.Tags.AUTHENTICATION,
    reporting.Tags.SECURITY,
    reporting.Tags.NETWORK,
    reporting.Tags.SERVICES
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
        # When the configuration does not contain the PermitRootLogin directive and
        # the configuration file was locally modified, it will not get updated by
        # RPM and the user might be locked away from the server. Warn the user here.
        if not config.permit_root_login and config.modified:
            create_report([
                reporting.Title('Possible problems with remote login using root account'),
                reporting.Summary(
                    'OpenSSH configuration file does not explicitly state '
                    'the option PermitRootLogin in sshd_config file, '
                    'which will default in RHEL8 to "prohibit-password".'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Tags(COMMON_REPORT_TAGS),
                reporting.Remediation(
                    hint='If you depend on remote root logins using '
                         'passwords, consider setting up a different '
                         'user for remote administration or adding '
                         '"PermitRootLogin yes" to sshd_config.'
                ),
                reporting.Flags([reporting.Flags.INHIBITOR])
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
                reporting.Tags(COMMON_REPORT_TAGS),
                reporting.Remediation(
                    hint='Consider using different user for administrative '
                         'logins or make sure your configration file '
                         'contains the line "PermitRootLogin yes" '
                         'in global context if desired.'
                ),
                reporting.Flags([reporting.Flags.INHIBITOR])
            ] + resources)
