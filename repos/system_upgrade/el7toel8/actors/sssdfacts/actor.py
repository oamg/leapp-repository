from six.moves import configparser

from leapp.actors import Actor
from leapp.libraries.actor.sssdfacts import SSSDFactsLibrary
from leapp.models import SSSDConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class SSSDFacts(Actor):
    """
    Check SSSD configuration for changes in RHEL8 and report them in model.

    These changes are:
    - id_provider=local is no longer supported and will be ignored
    - ldap_groups_use_matching_rule_in_chain was removed and will be ignored
    - ldap_initgroups_use_matching_rule_in_chain was removed and will be ignored
    - ldap_sudo_include_regexp changed default from true to false
    """

    name = 'sssd_facts'
    consumes = ()
    produces = (SSSDConfig,)
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
