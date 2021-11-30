from leapp.actors import Actor
from leapp.libraries.actor import opensshprotocolcheck
from leapp.models import OpenSshConfig, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


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
        opensshprotocolcheck.process(self.consume(OpenSshConfig))
