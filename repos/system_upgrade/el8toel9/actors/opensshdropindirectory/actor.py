from leapp.actors import Actor
from leapp.libraries.actor import opensshdropindirectory
from leapp.models import InstalledRedHatSignedRPM, OpenSshConfig
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class OpenSshDropInDirectory(Actor):
    """
    The RHEL 9 provides default configuration file with an Include directive.

    If the configuration file was modified, it will not be replaced by the update
    and we need to do couple of tweaks:

     * Insert Include directive as expected by the rest of the OS
     * Verify the resulting configuration is valid
       * The only potentially problematic option is "Subsystem", but it is kept in the
         main sshd_config even in RHEL9 so there is no obvious upgrade path where it
         could cause issues (unlike the Debian version).

    [1] https://bugzilla.mindrot.org/show_bug.cgi?id=3236
    """

    name = 'open_ssh_drop_in_directory'
    consumes = (OpenSshConfig, InstalledRedHatSignedRPM,)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag,)

    def process(self):
        opensshdropindirectory.process(self.consume(OpenSshConfig))
