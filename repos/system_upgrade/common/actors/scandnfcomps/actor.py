from leapp.actors import Actor
from leapp.libraries.actor import scandnfcomps
from leapp.models import InstalledDNFComps
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanDNFComps(Actor):
    """
    Scan installed DNF comps (environments and groups).

    Collects information about DNF package environments and groups that are
    currently installed on the source system and produce InstalledDNFComps
    message.
    """

    name = 'scan_dnf_comps'
    consumes = ()
    produces = (InstalledDNFComps,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scandnfcomps.process()
