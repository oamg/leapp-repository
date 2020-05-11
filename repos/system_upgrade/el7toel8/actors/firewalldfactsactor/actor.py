import os
import xml.etree.ElementTree as ElementTree

from leapp.actors import Actor
from leapp.libraries.actor import firewalldfactsactor
from leapp.models import FirewalldFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class FirewalldFactsActor(Actor):
    """
    Provide data about firewalld

    After collecting data, a message with relevant data will be produced.
    """

    name = 'firewalld_facts_actor'
    consumes = ()
    produces = (FirewalldFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = FirewalldFacts()

        try:
            tree = ElementTree.parse('/etc/firewalld/lockdown-whitelist.xml')
            root = tree.getroot()
            facts.firewall_config_command = firewalldfactsactor.getLockdownFirewallConfigCommand(root)
        except IOError:
            pass

        try:
            tree = ElementTree.parse('/etc/firewalld/direct.xml')
            root = tree.getroot()
            facts.ebtablesTablesInUse = firewalldfactsactor.getEbtablesTablesInUse(root)
        except IOError:
            pass

        ipsetTypesInUse = set()
        directory = '/etc/firewalld/ipsets'
        try:
            for filename in os.listdir(directory):
                if not filename.endswith('.xml'):
                    continue
                try:
                    tree = ElementTree.parse(os.path.join(directory, filename))
                    root = tree.getroot()
                    ipsetTypesInUse |= set(firewalldfactsactor.getIpsetTypesInUse(root))
                except IOError:
                    pass
            facts.ipsetTypesInUse = list(ipsetTypesInUse)
        except OSError:
            pass

        self.produce(facts)
