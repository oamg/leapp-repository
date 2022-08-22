from six.moves import configparser

from leapp.actors import Actor
from leapp.libraries.actor.sssdfacts8to9 import SSSDFactsLibrary
from leapp.models import SSSDConfig8to9
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class SSSDFacts8to9(Actor):
    """
    Check SSSD configuration for changes in RHEL9 and report them in model.

    Implicit files domain is disabled by default. This may affect local
    smartcard authentication if there is not explicit files domain created.

    If there is no files domain and smartcard authentication is enabled,
    we will notify the administrator.
    """

    name = 'sssd_facts_8to9'
    consumes = ()
    produces = (SSSDConfig8to9,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        try:
            config = configparser.RawConfigParser()
            config.read('/etc/sssd/sssd.conf')
        except configparser.Error:
            # SSSD is not configured properly. Nothing to do.
            self.log.warning('SSSD configuration unreadable.')
            return

        self.produce(SSSDFactsLibrary(config).process())
