from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.models import Report, OpenSshConfig
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import api
from leapp.reporting import create_report
from leapp import reporting


class OpenSshProtocolCheck(Actor):
    """
    Protocol configuration option was removed.

    Check the value of Protocol in OpenSSH server config file
    and warn about its deprecation if it is set. This option was removed
    in RHEL 7.4, but it might still be hanging around.
    """

    name = 'open_ssh_protocol'
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

        if config.protocol:
            create_report([
                reporting.Title('OpenSSH configured with removed configuration Protocol'),
                reporting.Summary(
                    'OpenSSH is configured with removed configuration '
                    'option Protocol. If this used to be for enabling '
                    'SSHv1, this is no longer supported in RHEL 8. '
                    'Otherwise this option can be simply removed.'
                ),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Tags([
                        reporting.Tags.AUTHENTICATION,
                        reporting.Tags.SECURITY,
                        reporting.Tags.NETWORK,
                        reporting.Tags.SERVICES
                ]),
            ])
