from leapp.actors import Actor
from leapp.models import Report, OpenSshConfig
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import api
from leapp.libraries.common.reporting import report_generic


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
        config = next(openssh_messages)
        if list(openssh_messages):
            api.current_logger().warning('Unexpectedly received more than one OpenSshConfig message.')

        if config.protocol:
            report_generic(
                title='OpenSSH configured with removed configuration Protocol',
                summary='OpenSSH is configured with removed configuration '
                        'option Protocol. If this used to be for enabling '
                        'SSHv1, this is no longer supported in RHEL 8. '
                        'Otherwise this option can be simply removed.',
                severity='low')
