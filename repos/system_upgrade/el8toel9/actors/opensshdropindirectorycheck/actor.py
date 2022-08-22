from leapp import reporting
from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, OpenSshConfig, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class OpenSshDropInDirectoryCheck(Actor):
    """
    Trigger a notice that the main sshd_config will be updated to contain
    the Include directive so the other configuration files dropped by the
    RHEL9 packages are effective.

    This might change the sshd behavior so it is advised to verify by the
    customer that the updated system behaves as expected.
    """

    name = 'open_ssh_drop_in_directory_check'
    consumes = (OpenSshConfig, InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag,)

    def process(self):
        openssh_messages = self.consume(OpenSshConfig)
        config = next(openssh_messages, None)
        if list(openssh_messages):
            api.current_logger().warning('Unexpectedly received more than one OpenSshConfig message.')
        if not config:
            raise StopActorExecutionError(
                'Could not check openssh configuration', details={'details': 'No OpenSshConfig facts found.'}
            )

        # If the package is not installed, there is no need to do anything
        if not has_package(InstalledRedHatSignedRPM, 'openssh-server'):
            return

        # If the configuration file was not modified, the rpm update will bring the new
        # changes by itself
        if not config.modified:
            return

        # otherwise we will prepend the Include directive to the main sshd_config
        resources = [
            reporting.RelatedResource('package', 'openssh-server'),
            reporting.RelatedResource('file', '/etc/ssh/sshd_config')
        ]
        reporting.create_report([
            reporting.Title('The upgrade will prepend the Incude directive to OpenSSH sshd_config'),
            reporting.Summary(
                'OpenSSH server configuration needs to be modified to contain Include directive '
                'for the RHEL9 to work properly and integrate with the other parts of the OS. '
                'The following snippet will be added to the /etc/ssh/sshd_config during the '
                'ApplicationsPhase: `Include /etc/ssh/sshd_config.d/*.conf`'
            ),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES
            ]),
        ] + resources)
