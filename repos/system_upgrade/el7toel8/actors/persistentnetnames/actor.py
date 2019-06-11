from leapp.actors import Actor
from leapp.libraries.common import persistentnetnames
from leapp.models import PersistentNetNamesFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class PersistentNetNames(Actor):
    """
    Get network interface information for physical ethernet interfaces of the original system.

    Gather information like PCI topology, MAC address and interface name on the
    original system. Those data are provided through the PersistentNetNamesFacts
    model.

    See the persistentnetnamesinitramfs actor that is very same but processed
    during early phases in initrams to gather the same data but using already
    new kernel of the target system to be able to reflect changes affected
    by the new kernel (see the PersistentNetNamesConfig actor).
    """

    name = 'persistentnetnames'
    consumes = ()
    produces = (PersistentNetNamesFacts, )
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(PersistentNetNamesFacts(interfaces=list(persistentnetnames.interfaces())))
