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

    if config.use_privilege_separation is not None and \
       config.use_privilege_separation != "sandbox":
        reporting.create_report([
            reporting.Title('OpenSSH configured not to use privilege separation sandbox'),
            reporting.Summary(
                'OpenSSH is configured to disable privilege '
                'separation sandbox, which is decreasing security '
                'and is no longer supported in RHEL 8'
            ),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES
            ]),
        ])
