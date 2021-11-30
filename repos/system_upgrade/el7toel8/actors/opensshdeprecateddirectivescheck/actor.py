from leapp.actors import Actor
from leapp.libraries.actor.opensshdeprecateddirectivescheck import inhibit_if_deprecated_directives_used
from leapp.models import OpenSshConfig, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class OpenSshDeprecatedDirectivesCheck(Actor):
    """
    Check for any deprecated directives in the OpenSSH configuration.

    Checks the directives used in the OpenSSH configuration for ones that have
    been deprecated and their usage in newer versions would result in the sshd
    service failing to start after the upgrade.
    """

    name = 'open_ssh_deprecated_directives_check'
    consumes = (OpenSshConfig,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        ssh_config = next(self.consume(OpenSshConfig))
        inhibit_if_deprecated_directives_used(ssh_config)
