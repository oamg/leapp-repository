from leapp.actors import Actor
from leapp.libraries.actor import sssdfacts
from leapp.models import SSSDConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class SSSDFacts(Actor):
    """
    Check SSSD configuration for changes in RHEL10 and report them in model.

    We want to know if the 'ssh' service is enabled and whether ssh was
    configured to use the sss_ssh_knownhosts tool.
    """

    name = 'sssd_facts'
    consumes = ()
    produces = (SSSDConfig,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        self.produce(sssdfacts.get_facts(['/etc/sssd/sssd.conf', '/etc/sssd/conf.d/'],
                                         ['/etc/ssh/ssh_config', '/etc/ssh/ssh_config.d/']))
