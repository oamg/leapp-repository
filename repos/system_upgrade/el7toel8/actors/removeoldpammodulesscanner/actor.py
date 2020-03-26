from leapp.actors import Actor
from leapp.libraries.actor.library import RemoveOldPAMModulesScannerLibrary
from leapp.libraries.common.pam import PAM
from leapp.models import RemovedPAMModules
from leapp.tags import IPUWorkflowTag, FactsPhaseTag, ExperimentalTag


class RemoveOldPAMModulesScanner(Actor):
    """
    Scan PAM configuration for modules that are not available in RHEL-8.

    PAM module pam_krb5 and pam_pkcs11 are no longer present in RHEL-8
    and must be removed from PAM configuration, otherwise it may lock out
    the system.
    """
    name = 'removed_pam_modules_scanner'
    consumes = ()
    produces = (RemovedPAMModules,)
    tags = (IPUWorkflowTag, FactsPhaseTag, ExperimentalTag)

    def process(self):
        pam = PAM.from_system_configuration()
        scanner = RemoveOldPAMModulesScannerLibrary(pam)
        self.produce(scanner.process())
