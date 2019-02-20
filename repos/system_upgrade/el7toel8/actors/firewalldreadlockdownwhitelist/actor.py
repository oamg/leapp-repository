from leapp.actors import Actor
from leapp.models import FirewalldLockdownWhitelist
from leapp.tags import FactsPhaseTag, IPUWorkflowTag

from leapp.libraries.actor import private

import xml.etree.ElementTree as ElementTree


class FirewalldReadLockdownWhitelist(Actor):
    """
    Provides data about firewalld Lockdown Whitelist

    After collecting data from the configuration file, a message with relevant
    data will be produced.
    """

    name = 'firewalld_read_lockdown_whitelist'
    consumes = ()
    produces = (FirewalldLockdownWhitelist,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        tree = ElementTree.parse('/etc/firewalld/lockdown-whitelist.xml')
        root = tree.getroot()

        self.produce(private.getFirewalldLockdownWhitelistFromXML(root))
