from leapp.actors import Actor
from leapp.libraries.actor import readopensshconfig
from leapp.models import OpenSshConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class OpenSshConfigScanner(Actor):
    """
    Collect information about the OpenSSH configuration.

    Currently supporting the following options:

     * PermitRootLogin
     * UsePrivilegeSeparation
     * Protocol
     * Ciphers
     * MACs
     * Subsystem sftp

    """

    name = 'read_openssh_config'
    consumes = ()
    produces = (OpenSshConfig, )
    tags = (FactsPhaseTag, IPUWorkflowTag, )

    def process(self):
        readopensshconfig.scan_sshd(self.produce)
