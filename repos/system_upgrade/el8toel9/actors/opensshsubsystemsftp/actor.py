from leapp.actors import Actor
from leapp.libraries.actor import opensshsubsystemsftp
from leapp.models import InstalledRedHatSignedRPM, OpenSshConfig
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class OpenSshSubsystemSftp(Actor):
    """
    The RHEL9 changes the SCP to use SFTP protocol internally. The both RHEL8 and RHEL9
    enable SFTP server by default, but if the user disabled the SFTP for some reason,
    it might make sense to warn that some previously working SCP operations could stop
    working.
    """

    name = 'open_ssh_subsystem_sftp'
    consumes = (OpenSshConfig, InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        opensshsubsystemsftp.process(self.consume(OpenSshConfig))
