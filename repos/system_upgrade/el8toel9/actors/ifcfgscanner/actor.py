from leapp.actors import Actor
from leapp.libraries.actor import ifcfgscanner
from leapp.models import IfCfg
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class IfCfgScanner(Actor):
    """
    Scan ifcfg files with legacy network configuration
    """

    name = "ifcfg_scanner"
    consumes = ()
    produces = (IfCfg,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        ifcfgscanner.process()
