from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.models import InstalledRedHatSignedRPM, VsftpdFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class VsftpdConfigRead(Actor):
    '''
    Reads vsftpd configuration files (/etc/vsftpd/*.conf) and extracts necessary information.
    '''

    name = 'vsftpd_config_read'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (VsftpdFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        installed_rpm_facts = next(self.consume(InstalledRedHatSignedRPM))
        if library.is_processable(installed_rpm_facts):
            self.produce(library.get_vsftpd_facts())
