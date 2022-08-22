from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp import reporting


def process(openssh_messages):
    config = next(openssh_messages, None)
    if list(openssh_messages):
        api.current_logger().warning('Unexpectedly received more than one OpenSshConfig message.')
    if not config:
        raise StopActorExecutionError(
            'Could not check openssh configuration', details={'details': 'No OpenSshConfig facts found.'}
        )

    if config.protocol:
        reporting.create_report([
            reporting.Title('OpenSSH configured with removed configuration Protocol'),
            reporting.Summary(
                'OpenSSH is configured with removed configuration '
                'option Protocol. If this used to be for enabling '
                'SSHv1, this is no longer supported in RHEL 8. '
                'Otherwise this option can be simply removed.'
            ),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES
            ]),
        ])
