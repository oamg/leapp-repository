from leapp.actors import Actor
from leapp.libraries.actor import updates
from leapp.libraries.common import rpms
from leapp.models import BindFacts, InstalledRedHatSignedRPM
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class BindUpdate(Actor):
    """
    Actor parsing facts found in configuration and modifying configuration.
    """

    name = 'bind_update'
    consumes = (InstalledRedHatSignedRPM, BindFacts)
    produces = ()
    tags = (PreparationPhaseTag, IPUWorkflowTag)

    pkg_names = {'bind', 'bind-sdb', 'bind-pkcs11'}

    def has_bind_package(self):
        """Test any bind server package is installed."""
        for pkg in self.pkg_names:
            if rpms.has_package(InstalledRedHatSignedRPM, pkg):
                return True
        return False

    def process(self):
        if not self.has_bind_package():
            self.log.debug('bind is not installed')
            return

        for bindfacts in self.consume(BindFacts):
            updates.update_facts(bindfacts)
            self.log.info('BIND configuration files modified: %s',
                          ', '.join(bindfacts.modified_files))
